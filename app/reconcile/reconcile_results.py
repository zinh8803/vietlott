"""Đối chiếu prediction với kết quả chính thức."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import Draw, Metric, Prediction, RetrainJob


def reconcile_pending(db: Session, product_code: str) -> list[Prediction]:
    """Đối chiếu tất cả predictions đang ở trạng thái pending_result."""
    pending = db.execute(
        select(Prediction).where(
            Prediction.product_code == product_code,
            Prediction.status == "pending_result",
        )
    ).scalars().all()

    reconciled: list[Prediction] = []
    for pred in pending:
        actual_draw = db.execute(
            select(Draw).where(
                Draw.product_code == product_code,
                Draw.draw_no == pred.predicted_draw_no,
            )
        ).scalar_one_or_none()

        if not actual_draw:
            continue  # Chưa có kết quả

        actual_numbers = {n for n in actual_draw.numbers if n > 0}
        predicted_numbers = set(pred.top6_json)

        hit_count = len(predicted_numbers & actual_numbers)
        hit_bonus = (
            pred.probabilities_json is not None
            and actual_draw.bonus_number is not None
            and actual_draw.bonus_number in predicted_numbers
        )

        pred.actual_top6_json = actual_draw.numbers
        pred.actual_bonus_number = actual_draw.bonus_number
        pred.hit_count_main = hit_count
        pred.hit_bonus = hit_bonus
        pred.status = "reconciled"
        pred.reconciled_at = datetime.utcnow()

        # Ghi metric live
        from app.core.config import get_settings
        settings = get_settings()
        cfg = settings.products.get(product_code, {})
        top_n = cfg.get("top_n", 6)

        p6 = hit_count / float(top_n)
        metric = Metric(
            model_id=pred.model_id,
            product_code=product_code,
            eval_scope="live",
            period_from_draw_id=pred.as_of_draw_id,
            period_to_draw_id=actual_draw.draw_id,
            precision_at_6=p6,
            metric_json={
                "hit_count": hit_count,
                "hit_bonus": hit_bonus,
                "predicted_draw_no": pred.predicted_draw_no,
            },
        )
        db.add(metric)
        reconciled.append(pred)

        logger.info(
            f"Reconciled {product_code} kỳ {pred.predicted_draw_no}: "
            f"hit={hit_count}/{top_n}, p@{top_n}={p6:.3f}"
        )

    db.commit()
    return reconciled
