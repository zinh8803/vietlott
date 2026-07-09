"""Celery tasks cho tất cả pipeline operations."""
from __future__ import annotations

from loguru import logger

from app.workers.celery_app import celery_app
from app.db.database import SessionLocal
from app.core.config import get_settings

settings = get_settings()


@celery_app.task(bind=True, name="tasks.sync_draws")
def sync_draws_task(self, product_code: str, force: bool = False):
    """Task: Đồng bộ kết quả kỳ quay từ vietlott.vn."""
    from app.crawlers.vietlott_crawler import sync_draws
    db = SessionLocal()
    try:
        draws = sync_draws(db, product_code, force=force)
        return {"status": "ok", "draws_synced": len(draws)}
    except Exception as exc:
        logger.exception(f"sync_draws_task lỗi: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=3)
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.build_features")
def build_features_task(self, product_code: str, window_size: int = 20, feature_version: str = "v1"):
    """Task: Build sliding window features."""
    from app.features.sliding_window import build_all_features
    db = SessionLocal()
    cfg = settings.products.get(product_code, {})
    number_space = cfg.get("number_space", 45)
    try:
        n_train, n_valid, n_test = build_all_features(
            db, product_code, window_size, feature_version,
            holdout_draws=settings.training.get("holdout_draws", 30),
            number_space=number_space,
        )
        return {"status": "ok", "n_train": n_train, "n_valid": n_valid, "n_test": n_test}
    except Exception as exc:
        logger.exception(f"build_features_task lỗi: {exc}")
        raise self.retry(exc=exc, countdown=30, max_retries=2)
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.train_all")
def train_all_task(self, product_code: str, window_size: int = 20, feature_version: str = "v1"):
    """Task: Train tất cả models và promote champion."""
    from app.train.train_baseline import train_baselines
    from app.train.train_lightgbm import train_lightgbm
    from app.train.train_xgboost import train_xgboost
    from app.train.select_champion import promote_champion
    db = SessionLocal()
    try:
        results = {}
        baselines = train_baselines(db, product_code, feature_version, window_size,
                                    artifact_root=settings.artifact_root)
        results["baselines"] = len(baselines)

        lgbm_model = train_lightgbm(db, product_code, feature_version, window_size,
                                     artifact_root=settings.artifact_root)
        results["lightgbm"] = lgbm_model.model_id if lgbm_model else None

        xgb_model = train_xgboost(db, product_code, feature_version, window_size,
                                   artifact_root=settings.artifact_root)
        results["xgboost"] = xgb_model.model_id if xgb_model else None

        champion = promote_champion(db, product_code)
        results["champion"] = champion.model_id if champion else None

        return {"status": "ok", **results}
    except Exception as exc:
        logger.exception(f"train_all_task lỗi: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=1)
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.auto_retrain_products")
def auto_retrain_products_task(
    self,
    product_codes: list[str],
    window_size: int | None = None,
    feature_version: str = "v1",
    force: bool = True,
):
    """Task: retrain Mega 6/45 and Power 6/55 from latest stored results."""
    from app.train.auto_retrain import auto_retrain_products_from_results
    db = SessionLocal()
    try:
        results = auto_retrain_products_from_results(
            db,
            products=product_codes,
            window_size=window_size,
            feature_version=feature_version,
            force=force,
        )
        return {"status": "ok", "results": results}
    except Exception as exc:
        logger.exception(f"auto_retrain_products_task lá»—i: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=1)
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.learn_from_results")
def learn_from_results_task(
    self,
    product_codes: list[str],
    sync_latest: bool = True,
    count: int = 1,
    window_size: int | None = None,
    feature_version: str = "v1",
    force_retrain: bool = False,
):
    """Task: sync results, reconcile hits, then retrain selected products."""
    from app.reconcile.reconcile_results import reconcile_pending
    from app.train.auto_retrain import auto_retrain_products_from_results
    db = SessionLocal()
    try:
        synced: dict[str, int] = {}
        reconciled_counts: dict[str, int] = {}

        if sync_latest:
            from app.crawlers.vietlott_crawler import sync_draws
            for product_code in product_codes:
                draws = sync_draws(db, product_code, count=count)
                synced[product_code] = len(draws)

        for product_code in product_codes:
            reconciled = reconcile_pending(db, product_code)
            reconciled_counts[product_code] = len(reconciled)

        train_results = auto_retrain_products_from_results(
            db,
            products=product_codes,
            reconciled_counts=reconciled_counts,
            window_size=window_size,
            feature_version=feature_version,
            force=force_retrain,
        )
        return {
            "status": "ok",
            "synced": synced,
            "reconciled": reconciled_counts,
            "train_results": train_results,
        }
    except Exception as exc:
        logger.exception(f"learn_from_results_task lá»—i: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=1)
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.predict_next")
def predict_next_task(self, product_code: str):
    """Task: Sinh dự đoán kỳ kế tiếp."""
    from app.predict.generate_next_prediction import generate_next_prediction
    db = SessionLocal()
    cfg = settings.products.get(product_code, {})
    number_space = cfg.get("number_space", 45)
    try:
        pred = generate_next_prediction(db, product_code, number_space=number_space)
        if pred:
            return {"status": "ok", "prediction_id": pred.prediction_id, "top6": pred.top6_json}
        return {"status": "no_champion"}
    except Exception as exc:
        logger.exception(f"predict_next_task lỗi: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=2)
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.reconcile")
def reconcile_task(self, product_code: str):
    """Task: Đối chiếu pending predictions."""
    from app.reconcile.reconcile_results import reconcile_pending
    db = SessionLocal()
    try:
        reconciled = reconcile_pending(db, product_code)
        return {"status": "ok", "reconciled_count": len(reconciled)}
    except Exception as exc:
        logger.exception(f"reconcile_task lỗi: {exc}")
        raise self.retry(exc=exc, countdown=60, max_retries=2)
    finally:
        db.close()
