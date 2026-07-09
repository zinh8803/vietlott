"""Train baseline models: DummyClassifier, LogisticRegression, RandomForestClassifier.

Dùng scikit-learn Pipeline để tránh data leakage.
"""
from __future__ import annotations

import os
import hashlib
import json
import joblib
from datetime import datetime
from pathlib import Path

import numpy as np
from loguru import logger
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import log_loss, brier_score_loss
from sqlalchemy.orm import Session

from app.db.models import Model, Metric
from app.features.sliding_window import get_feature_matrix


def _precision_at_6(y_true: np.ndarray, y_prob: np.ndarray, product_code: str = "MEGA_645") -> float:
    """Precision@6 (hoặc Precision@3 cho BINGO18): tỷ lệ số trúng trong top-k xếp hạng xác suất.
    Tính trên tất cả target draws.
    """
    top_n = 3 if product_code == "BINGO18" else 6
    total = len(y_true)
    precisions = []
    i = 0
    
    if product_code == "BINGO18":
        # BINGO18 has exactly 6 candidates per draw
        draw_size = 6
        while i < total:
            best_j = min(i + draw_size, total)
            group_true = y_true[i:best_j]
            group_prob = y_prob[i:best_j]
            top_idx = np.argsort(group_prob)[::-1][:top_n]
            hits = group_true[top_idx].sum()
            precisions.append(hits / float(top_n))
            i = best_j
    else:
        # Mega / Power
        while i < total:
            # Scan forward để tìm group (tối đa 55 row)
            best_j = i + 6
            for j in range(i + 30, min(i + 60, total + 1)):
                if y_true[i:j].sum() == 6:
                    best_j = j
                    break
            group_true = y_true[i:best_j]
            group_prob = y_prob[i:best_j]
            top_idx = np.argsort(group_prob)[::-1][:top_n]
            hits = group_true[top_idx].sum()
            precisions.append(hits / float(top_n))
            i = best_j

    return float(np.mean(precisions)) if precisions else 0.0


def _save_model(clf, artifact_root: str, product_code: str, model_name: str) -> tuple[str, str]:
    """Lưu model bằng joblib, trả (artifact_uri, checksum)."""
    path = Path(artifact_root) / "models" / product_code / f"{model_name}.joblib"
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, path)
    checksum = hashlib.sha256(path.read_bytes()).hexdigest()
    return str(path), checksum


def train_baselines(
    db: Session,
    product_code: str,
    feature_version: str = "v1",
    window_size: int = 20,
    artifact_root: str = "./artifacts",
) -> list[Model]:
    """Train 3 baseline models và lưu vào DB."""
    logger.info(f"Training baselines cho {product_code} ...")

    X_train, y_train = get_feature_matrix(db, product_code, feature_version, ["train"], window_size)
    X_valid, y_valid = get_feature_matrix(db, product_code, feature_version, ["valid"], window_size)

    if X_train.shape[0] == 0:
        logger.error("Không có feature data! Chạy build_features trước.")
        return []

    # --- Lấy train/valid draw range để ghi vào metadata ---
    from app.db.models import Feature
    from sqlalchemy import select, func as sqlfunc
    draw_range = db.execute(
        select(
            sqlfunc.min(Feature.target_draw_id),
            sqlfunc.max(Feature.target_draw_id),
        ).where(
            Feature.product_code == product_code,
            Feature.feature_version == feature_version,
            Feature.dataset_role == "train",
        )
    ).one()
    train_from, train_to = draw_range

    valid_range = db.execute(
        select(
            sqlfunc.min(Feature.target_draw_id),
            sqlfunc.max(Feature.target_draw_id),
        ).where(
            Feature.product_code == product_code,
            Feature.feature_version == feature_version,
            Feature.dataset_role == "valid",
        )
    ).one()
    valid_from, valid_to = valid_range

    import sklearn
    import platform

    framework_versions = {
        "sklearn": sklearn.__version__,
        "python": platform.python_version(),
    }

    trained_models: list[Model] = []

    configs = [
        ("dummy", DummyClassifier(strategy="stratified"), False),
        ("logreg", LogisticRegression(max_iter=1000, C=0.1, random_state=42), True),
        ("random_forest", RandomForestClassifier(
            n_estimators=100, max_depth=6, min_samples_leaf=20, random_state=42, n_jobs=-1
        ), False),
    ]

    for algo_name, clf_raw, use_scaler in configs:
        logger.info(f"  Training {algo_name}...")

        if use_scaler:
            clf = Pipeline([("scaler", StandardScaler()), ("clf", clf_raw)])
        else:
            clf = clf_raw

        clf.fit(X_train, y_train)

        # Metrics trên valid
        y_prob_valid = clf.predict_proba(X_valid)[:, 1]
        ll = log_loss(y_valid, y_prob_valid)
        bs = brier_score_loss(y_valid, y_prob_valid)
        p6 = _precision_at_6(y_valid, y_prob_valid, product_code)

        hyperparams = {
            "algorithm": algo_name,
            "use_scaler": use_scaler,
        }

        model_name = f"{product_code}_{algo_name}_{feature_version}_w{window_size}"
        artifact_uri, checksum = _save_model(clf, artifact_root, product_code, model_name)

        db_model = Model(
            model_name=model_name,
            algorithm=algo_name,
            product_code=product_code,
            task_type="binary_classification",
            feature_version=feature_version,
            window_size=window_size,
            train_from_draw_id=train_from or 1,
            train_to_draw_id=train_to or 1,
            valid_from_draw_id=valid_from,
            valid_to_draw_id=valid_to,
            hyperparams_json=hyperparams,
            metrics_summary_json={"log_loss": ll, "brier_score": bs, "precision_at_6": p6},
            artifact_uri=artifact_uri,
            model_checksum=checksum,
            framework_versions_json=framework_versions,
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
            metric_json={"precision_at_6": p6, "log_loss": ll, "brier_score": bs},
        )
        db.add(metric)
        db.flush()

        trained_models.append(db_model)
        logger.info(f"    {algo_name}: p@6={p6:.4f}, log_loss={ll:.4f}, brier={bs:.4f}")

    db.commit()
    return trained_models
