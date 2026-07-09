"""Champion selection: so sánh models theo holdout metrics, promote best model."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

import joblib
import numpy as np
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import Metric, Model, RetrainJob
from app.features.sliding_window import get_feature_matrix


def get_best_model(
    db: Session,
    product_code: str,
    metric: str = "precision_at_6",
) -> Optional[Model]:
    """Lấy model có metric tốt nhất trên holdout set.
    Ưu tiên: lightgbm > xgboost > random_forest > logreg > dummy.
    """
    models = db.execute(
        select(Model).where(
            Model.product_code == product_code,
            Model.status.in_(["challenger", "champion"]),
        )
    ).scalars().all()

    if not models:
        return None

    # Priority: thuật toán tốt hơn thắng khi metric bằng nhau
    algo_priority = {"lightgbm": 5, "xgboost": 4, "random_forest": 3, "logreg": 2, "dummy": 1}

    best = None
    best_val = -1.0
    best_priority = -1
    for m in models:
        if m.metrics_summary_json:
            val = m.metrics_summary_json.get(metric, -1.0)
            if val is None:
                continue
            priority = algo_priority.get(m.algorithm, 0)
            # So sánh: metric tốt hơn thắng; nếu bằng nhau thì priority cao hơn thắng
            if val > best_val + 1e-6 or (abs(val - best_val) < 1e-6 and priority > best_priority):
                best_val = val
                best_priority = priority
                best = m

    return best


def promote_champion(db: Session, product_code: str) -> Optional[Model]:
    """Demote champion cũ, promote model tốt nhất thành champion."""
    best = get_best_model(db, product_code)
    if not best:
        logger.warning(f"Không tìm thấy model nào cho {product_code}")
        return None

    # Demote tất cả champion cũ
    old_champions = db.execute(
        select(Model).where(
            Model.product_code == product_code,
            Model.status == "champion",
            Model.model_id != best.model_id,
        )
    ).scalars().all()

    for champ in old_champions:
        champ.status = "retired"
        logger.info(f"Retired champion: {champ.model_name}")

    best.status = "champion"
    best.promoted_at = datetime.utcnow()
    db.commit()

    logger.info(
        f"Promoted champion: {best.model_name} "
        f"(p@6={best.metrics_summary_json.get('precision_at_6', 'N/A')})"
    )
    return best


def get_champion(db: Session, product_code: str) -> Optional[Model]:
    """Lấy champion hiện tại – dùng .limit(1) để tránh MultipleResultsFound."""
    return db.execute(
        select(Model).where(
            Model.product_code == product_code,
            Model.status == "champion",
        ).order_by(Model.promoted_at.desc())
        .limit(1)
    ).scalar_one_or_none()



def load_champion_model(champion: Model):
    """Load model artifact từ filesystem."""
    return joblib.load(champion.artifact_uri)


def maybe_trigger_retrain(
    db: Session,
    product_code: str,
    min_new_draws: int = 3,
    precision_guardrail: float = 0.18,
) -> Optional[RetrainJob]:
    """Kiểm tra điều kiện retrain và tạo job nếu cần."""
    champion = get_champion(db, product_code)
    if not champion:
        return None

    # Kiểm tra số kỳ live kể từ lần train cuối
    from app.db.models import Prediction
    live_metrics = db.execute(
        select(Metric).where(
            Metric.model_id == champion.model_id,
            Metric.eval_scope == "live",
        ).order_by(Metric.created_at.desc()).limit(min_new_draws)
    ).scalars().all()

    if not live_metrics:
        return None

    # Kiểm tra precision guardrail
    recent_p6 = [m.precision_at_6 for m in live_metrics if m.precision_at_6 is not None]
    if recent_p6 and np.mean(recent_p6) < precision_guardrail:
        reason = f"Live precision@6={np.mean(recent_p6):.4f} < guardrail={precision_guardrail}"
        logger.warning(f"Kích hoạt retrain: {reason}")
        job = RetrainJob(
            product_code=product_code,
            trigger_reason=reason,
            status="pending",
        )
        db.add(job)
        db.commit()
        return job

    return None
