"""Sinh dự đoán kỳ kế tiếp cho product_code."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

import numpy as np
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import Draw, Prediction
from app.train.select_champion import get_champion, load_champion_model
from app.features.sliding_window import (
    _compute_candidate_features,
    _compute_draw_level_features,
    CANONICAL_FEATURE_KEYS,
)


def generate_next_prediction(
    db: Session,
    product_code: str,
    request_type: str = "scheduled",
    number_space: Optional[int] = None,
    random_sample: bool = False,
) -> Optional[Prediction]:
    """Sinh dự đoán cho kỳ kế tiếp.

    Quy trình:
    1. Xác định as_of_draw (kỳ gần nhất có kết quả).
    2. Build feature cho tất cả candidate_no dùng CANONICAL_FEATURE_KEYS.
    3. Gọi champion model → probabilities.
    4. Lấy top-6 xếp theo prob giảm dần (hoặc weighted random sampling).
    5. Lưu vào bảng predictions.
    """
    champion = get_champion(db, product_code)
    if not champion:
        logger.error(f"Không có champion model cho {product_code}")
        return None

    # Xác định as_of_draw – dùng .limit(1) để tránh MultipleResultsFound
    as_of_draw = db.execute(
        select(Draw)
        .where(Draw.product_code == product_code)
        .order_by(Draw.draw_no.desc())
        .limit(1)
    ).scalar_one_or_none()

    if not as_of_draw:
        logger.error(f"Không có draw data cho {product_code}")
        return None

    # Số không gian
    if number_space is None:
        from app.core.config import get_settings
        settings = get_settings()
        cfg = settings.products.get(product_code, {})
        number_space = cfg.get("number_space", 45 if product_code == "MEGA_645" else 55)

    # Predicted draw
    predicted_draw_no = as_of_draw.draw_no + 1
    predicted_draw_date = as_of_draw.draw_date + timedelta(days=3)  # approx

    # Nếu dùng random sampling, tạo request_type ngẫu nhiên để tránh đụng độ unique key
    if random_sample:
        import time
        import random
        # s_ + 6 ký tự timestamp + 2 ký tự ngẫu nhiên (tối đa 16 ký tự)
        request_type = f"s_{int(time.time()) % 1000000}_{random.randint(10, 99)}"[:16]

    # Kiểm tra đã có prediction chưa (chỉ kiểm tra khi không lấy mẫu ngẫu nhiên)
    if not random_sample:
        existing = db.execute(
            select(Prediction).where(
                Prediction.model_id == champion.model_id,
                Prediction.product_code == product_code,
                Prediction.predicted_draw_no == predicted_draw_no,
                Prediction.request_type == request_type,
            ).limit(1)
        ).scalar_one_or_none()

        if existing:
            logger.info(f"Prediction đã tồn tại cho {product_code} kỳ {predicted_draw_no}")
            return existing

    # Lấy toàn bộ history để build feature
    all_draws = db.execute(
        select(Draw)
        .where(Draw.product_code == product_code)
        .order_by(Draw.draw_no)
    ).scalars().all()

    from app.core.config import get_settings
    settings = get_settings()
    cfg = settings.products.get(product_code, {})
    top_n = cfg.get("top_n", 6)

    window_size = champion.window_size
    context = all_draws[-window_size:]
    draw_features = _compute_draw_level_features(context, number_space)

    # Build feature vector cho từng candidate – dùng CANONICAL_FEATURE_KEYS
    # để đảm bảo thứ tự keys và số chiều khớp hoàn toàn với lúc train
    X_pred = []
    for candidate in range(1, number_space + 1):
        cand_f = _compute_candidate_features(candidate, context, window_size, number_space)
        merged = {**cand_f, **draw_features}
        X_pred.append([merged.get(k, 0.0) for k in CANONICAL_FEATURE_KEYS])

    X_pred = np.array(X_pred, dtype=np.float32)

    # Load champion model và predict
    try:
        model = load_champion_model(champion)
        probs = model.predict_proba(X_pred)[:, 1]
    except Exception as exc:
        logger.error(f"Lỗi khi load/predict champion: {exc}")
        return None

    # Tạo probability map
    probabilities = {str(i + 1): float(probs[i]) for i in range(number_space)}

    # Sinh bộ số
    if random_sample:
        # Lấy mẫu ngẫu nhiên không hoàn lại theo trọng số xác suất
        p = np.array(probs, dtype=np.float64)
        p = np.clip(p, 0, None)
        # Cộng thêm epsilon để tránh lỗi khi có quá ít phần tử có xác suất > 0
        p += 1e-9
        p /= p.sum()
        
        sampled_indices = np.random.choice(number_space, size=top_n, replace=False, p=p)
        top6 = sorted([int(i + 1) for i in sampled_indices])
    else:
        # Lấy Top-N xác suất cao nhất cố định
        top_indices = np.argsort(probs)[::-1][:top_n]
        top6 = sorted([int(i + 1) for i in top_indices])

    prediction = Prediction(
        model_id=champion.model_id,
        product_code=product_code,
        as_of_draw_id=as_of_draw.draw_id,
        predicted_draw_no=predicted_draw_no,
        predicted_draw_date=predicted_draw_date,
        probabilities_json=probabilities,
        top6_json=top6,
        request_type=request_type,
        status="pending_result",
    )
    db.add(prediction)
    db.commit()

    logger.info(
        f"Prediction {product_code} kỳ {predicted_draw_no}: "
        f"top6={top6}, max_prob={float(probs.max()):.4f}, random_sample={random_sample}"
    )
    return prediction
