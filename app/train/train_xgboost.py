"""Train XGBoost classifier với binary:logistic objective."""
from __future__ import annotations

import platform
from pathlib import Path

import numpy as np
from loguru import logger
from sklearn.metrics import log_loss, brier_score_loss
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sqlalchemy.orm import Session
from sqlalchemy import select, func as sqlfunc

from app.db.models import Feature, Metric, Model
from app.features.sliding_window import get_feature_matrix
from app.train.train_baseline import _precision_at_6, _save_model


def train_xgboost(
    db: Session,
    product_code: str,
    feature_version: str = "v1",
    window_size: int = 20,
    artifact_root: str = "./artifacts",
    n_iter: int = 20,
    cv_folds: int = 5,
) -> Model | None:
    """Train XGBoost với RandomizedSearchCV."""
    try:
        from xgboost import XGBClassifier
        import xgboost as xgb
    except ImportError:
        logger.error("xgboost chưa được cài. Chạy: pip install xgboost")
        return None

    logger.info(f"Training XGBoost cho {product_code}...")

    X_train, y_train = get_feature_matrix(db, product_code, feature_version, ["train"], window_size)
    X_valid, y_valid = get_feature_matrix(db, product_code, feature_version, ["valid"], window_size)

    if X_train.shape[0] == 0:
        logger.error("Không có feature data!")
        return None

    param_dist = {
        "n_estimators": [100, 200, 500],
        "max_depth": [3, 4, 6, 8],
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "subsample": [0.7, 0.8, 0.9, 1.0],
        "colsample_bytree": [0.7, 0.8, 0.9, 1.0],
        "min_child_weight": [1, 5, 10, 20],
        "gamma": [0, 0.1, 0.5, 1.0],
        "reg_alpha": [0, 0.1, 0.5],
        "reg_lambda": [1.0, 2.0, 5.0],
    }

    base_clf = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        use_label_encoder=False,
        random_state=42,
        verbosity=0,
        n_jobs=-1,
    )

    tscv = TimeSeriesSplit(n_splits=cv_folds)
    search = RandomizedSearchCV(
        base_clf,
        param_distributions=param_dist,
        n_iter=n_iter,
        scoring="neg_log_loss",
        cv=tscv,
        random_state=42,
        verbose=0,
    )

    search.fit(X_train, y_train)
    best_clf = search.best_estimator_
    best_params = search.best_params_

    y_prob = best_clf.predict_proba(X_valid)[:, 1]
    ll = log_loss(y_valid, y_prob)
    bs = brier_score_loss(y_valid, y_prob)
    p6 = _precision_at_6(y_valid, y_prob, product_code)

    logger.info(f"XGBoost: p@6={p6:.4f}, log_loss={ll:.4f}, brier={bs:.4f}")

    draw_range = db.execute(
        select(sqlfunc.min(Feature.target_draw_id), sqlfunc.max(Feature.target_draw_id))
        .where(Feature.product_code == product_code, Feature.feature_version == feature_version, Feature.dataset_role == "train")
    ).one()
    train_from, train_to = draw_range

    valid_range = db.execute(
        select(sqlfunc.min(Feature.target_draw_id), sqlfunc.max(Feature.target_draw_id))
        .where(Feature.product_code == product_code, Feature.feature_version == feature_version, Feature.dataset_role == "valid")
    ).one()
    valid_from, valid_to = valid_range

    model_name = f"{product_code}_xgboost_{feature_version}_w{window_size}"
    artifact_uri, checksum = _save_model(best_clf, artifact_root, product_code, model_name)

    db_model = Model(
        model_name=model_name,
        algorithm="xgboost",
        product_code=product_code,
        task_type="binary_classification",
        feature_version=feature_version,
        window_size=window_size,
        train_from_draw_id=train_from or 1,
        train_to_draw_id=train_to or 1,
        valid_from_draw_id=valid_from,
        valid_to_draw_id=valid_to,
        hyperparams_json=best_params,
        metrics_summary_json={"log_loss": ll, "brier_score": bs, "precision_at_6": p6},
        artifact_uri=artifact_uri,
        model_checksum=checksum,
        framework_versions_json={"xgboost": xgb.__version__, "python": platform.python_version()},
        status="challenger",
    )
    db.add(db_model)
    db.flush()

    metric = Metric(
        model_id=db_model.model_id,
        product_code=product_code,
        eval_scope="holdout",
        period_from_draw_id=valid_from,
        period_to_draw_id=valid_to,
        precision_at_6=p6,
        log_loss=ll,
        brier_score=bs,
    )
    db.add(metric)
    db.commit()

    return db_model
