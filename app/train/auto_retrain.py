"""Helpers for retraining products after new official results arrive."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Draw, Model, RetrainJob
from app.features.sliding_window import build_all_features
from app.train.select_champion import get_champion, promote_champion
from app.train.train_baseline import train_baselines
from app.train.train_lightgbm import train_lightgbm
from app.train.train_xgboost import train_xgboost


DEFAULT_AUTO_TRAIN_PRODUCTS = ("MEGA_645", "POWER_655")


def _window_size_for_product(product_code: str, requested: int | None = None) -> int:
    if requested:
        return requested
    if product_code == "BINGO18":
        return 10
    return 20


def _latest_draw_id(db: Session, product_code: str) -> int | None:
    return db.execute(
        select(func.max(Draw.draw_id)).where(Draw.product_code == product_code)
    ).scalar()


def should_retrain_from_results(
    db: Session,
    product_code: str,
    reconciled_count: int = 0,
    min_new_draws: int | None = None,
    force: bool = False,
) -> tuple[bool, str]:
    """Decide if product should retrain after new draws/reconciled predictions."""
    settings = get_settings()
    if product_code not in settings.products:
        return False, f"unknown product {product_code}"

    if force:
        return True, "forced retrain"

    champion = get_champion(db, product_code)
    if not champion:
        return True, "no champion model"

    latest_draw_id = _latest_draw_id(db, product_code)
    if latest_draw_id is None:
        return False, "no draw data"

    if min_new_draws is None:
        min_new_draws = int(settings.training.get("min_new_draws_for_retrain", 3))

    new_draws = max(0, latest_draw_id - int(champion.train_to_draw_id or 0))
    if reconciled_count > 0:
        return True, f"{reconciled_count} predictions reconciled"
    if new_draws >= min_new_draws:
        return True, f"{new_draws} new draws since champion training"
    return False, f"only {new_draws} new draws since champion training"


def retrain_product_from_results(
    db: Session,
    product_code: str,
    window_size: int | None = None,
    feature_version: str = "v1",
    trigger_reason: str = "new official results",
) -> dict[str, Any]:
    """Build fresh features, train all algorithms, and promote a champion."""
    settings = get_settings()
    cfg = settings.products.get(product_code)
    if not cfg:
        raise ValueError(f"Unsupported product_code={product_code!r}")

    resolved_window = _window_size_for_product(product_code, window_size)
    number_space = int(cfg.get("number_space", 45))
    holdout_draws = int(settings.training.get("holdout_draws", 30))

    job = RetrainJob(
        product_code=product_code,
        trigger_reason=trigger_reason[:128],
        request_payload_json={
            "window_size": resolved_window,
            "feature_version": feature_version,
            "number_space": number_space,
            "holdout_draws": holdout_draws,
        },
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()

    try:
        n_train, n_valid, n_test = build_all_features(
            db=db,
            product_code=product_code,
            window_size=resolved_window,
            feature_version=feature_version,
            holdout_draws=holdout_draws,
            number_space=number_space,
        )

        baselines = train_baselines(
            db,
            product_code,
            feature_version,
            resolved_window,
            artifact_root=settings.artifact_root,
        )
        lgbm = train_lightgbm(
            db,
            product_code,
            feature_version,
            resolved_window,
            artifact_root=settings.artifact_root,
        )
        xgb = train_xgboost(
            db,
            product_code,
            feature_version,
            resolved_window,
            artifact_root=settings.artifact_root,
        )
        champion = promote_champion(db, product_code)

        job.status = "done"
        job.finished_at = datetime.utcnow()
        job.best_model_id = champion.model_id if champion else None
        db.commit()

        logger.info(
            "Retrained {} from results: champion={}",
            product_code,
            champion.model_id if champion else None,
        )
        return {
            "status": "trained",
            "job_id": job.job_id,
            "product_code": product_code,
            "trigger_reason": trigger_reason,
            "features": {"train": n_train, "valid": n_valid, "test": n_test},
            "baselines_trained": len(baselines),
            "lightgbm_model_id": lgbm.model_id if lgbm else None,
            "xgboost_model_id": xgb.model_id if xgb else None,
            "champion_model_id": champion.model_id if champion else None,
        }
    except Exception as exc:
        db.rollback()
        job.status = "failed"
        job.finished_at = datetime.utcnow()
        job.error_message = str(exc)
        db.add(job)
        db.commit()
        raise


def auto_retrain_products_from_results(
    db: Session,
    products: list[str] | tuple[str, ...] = DEFAULT_AUTO_TRAIN_PRODUCTS,
    reconciled_counts: dict[str, int] | None = None,
    window_size: int | None = None,
    feature_version: str = "v1",
    min_new_draws: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Run result-aware retraining for multiple products."""
    reconciled_counts = reconciled_counts or {}
    results: dict[str, Any] = {}

    for product_code in products:
        reconciled_count = int(reconciled_counts.get(product_code, 0))
        should_train, reason = should_retrain_from_results(
            db,
            product_code,
            reconciled_count=reconciled_count,
            min_new_draws=min_new_draws,
            force=force,
        )
        if not should_train:
            results[product_code] = {"status": "skipped", "reason": reason}
            continue

        results[product_code] = retrain_product_from_results(
            db,
            product_code,
            window_size=window_size,
            feature_version=feature_version,
            trigger_reason=reason,
        )

    return results
