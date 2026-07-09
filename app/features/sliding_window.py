"""Sliding window feature builder.

Với mỗi target_draw, build `number_space` record (45 cho Mega, 55 cho Power).
Nhãn = 1 nếu candidate_no nằm trong 6 số chính, ngược lại = 0.

Features được tính chỉ từ thông tin có trước target_draw (time-safe).
"""
from __future__ import annotations

import math
from datetime import date
from typing import Optional

import numpy as np
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import Draw, Feature


def _compute_candidate_features(
    candidate: int,
    history: list[Draw],
    window_size: int,
    number_space: int = 45,
) -> dict:
    """Tính feature vector cho một candidate number từ lịch sử window draws."""
    n = len(history)
    if n == 0:
        # Trả về feature zero vector khi không có lịch sử
        return {
            "freq": 0.0,
            "recency": window_size + 1,
            "gap_mean": float(window_size),
            "gap_std": 0.0,
            "ewma_freq": 0.0,
            "odd_even": int(candidate % 2 == 1),
            "low_high": int(candidate <= (number_space // 2)),
            "candidate_no": candidate,
            "window_size": window_size,
        }

    appearances = []
    for i, draw in enumerate(history):
        if candidate in draw.numbers:
            appearances.append(i)  # index từ quá khứ (0 = xa nhất)

    # Tần suất
    freq = len(appearances) / n

    # Recency: số kỳ kể từ lần xuất hiện gần nhất (tính ngược từ cuối)
    if appearances:
        recency = n - 1 - appearances[-1]  # 0 = xuất hiện ở kỳ gần nhất
    else:
        recency = n  # chưa bao giờ xuất hiện trong window

    # Gap giữa các lần xuất hiện
    if len(appearances) >= 2:
        gaps = [appearances[i+1] - appearances[i] for i in range(len(appearances)-1)]
        gap_mean = float(np.mean(gaps))
        gap_std = float(np.std(gaps))
    elif len(appearances) == 1:
        gap_mean = float(n)
        gap_std = 0.0
    else:
        gap_mean = float(n)
        gap_std = 0.0

    # EWMA frequency (decay = 0.9)
    alpha = 0.9
    ewma = 0.0
    for i, draw in enumerate(history):
        w = alpha ** (n - 1 - i)  # kỳ gần nhất có trọng số cao nhất
        ewma += w * int(candidate in draw.numbers)
    ewma /= sum(alpha ** k for k in range(n))

    return {
        "freq": round(freq, 6),
        "recency": recency,
        "gap_mean": round(gap_mean, 4),
        "gap_std": round(gap_std, 4),
        "ewma_freq": round(ewma, 6),
        "odd_even": int(candidate % 2 == 1),
        "low_high": int(candidate <= (number_space // 2)),
        "candidate_no": candidate,
        "window_size": n,
    }


def _compute_draw_level_features(history: list[Draw], number_space: int = 45) -> dict:
    """Feature mức window (aggregate toàn bộ draws)."""
    if not history:
        return {}
    # Lọc bỏ số 0 placeholder (cho BINGO18)
    all_nums = [n for d in history for n in d.numbers if n > 0]
    total = len(all_nums)
    if total == 0:
        return {
            "window_entropy": 0.0,
            "window_odd_rate": 0.0,
            "window_low_rate": 0.0,
            "window_draw_count": len(history),
        }
        
    # Entropy phân phối
    from collections import Counter
    cnt = Counter(all_nums)
    probs = [v / total for v in cnt.values()]
    entropy = -sum(p * math.log2(p) for p in probs if p > 0)

    # Tỉ lệ odd / even
    odd_rate = sum(1 for x in all_nums if x % 2 == 1) / total
    low_rate = sum(1 for x in all_nums if x <= (number_space // 2)) / total

    return {
        "window_entropy": round(entropy, 6),
        "window_odd_rate": round(odd_rate, 6),
        "window_low_rate": round(low_rate, 6),
        "window_draw_count": len(history),
    }


def build_features_for_draw(
    db: Session,
    target_draw: Draw,
    all_draws_before: list[Draw],
    window_size: int,
    feature_version: str,
    dataset_role: str = "train",
    number_space: int = 45,
    overwrite: bool = False,
) -> list[Feature]:
    """Build feature cho một target_draw cụ thể.

    Args:
        db: SQLAlchemy session.
        target_draw: Kỳ mục tiêu (label = numbers của kỳ này).
        all_draws_before: Tất cả draws TRƯỚC target_draw (time-safe).
        window_size: Số kỳ lịch sử dùng làm context.
        feature_version: Version string (e.g. "v1").
        dataset_role: "train" / "valid" / "test".
        number_space: 45 cho Mega, 55 cho Power, 6 cho Bingo18.
        overwrite: Nếu True, xóa feature cũ trước khi tạo mới.
    """
    # Lấy window_size kỳ gần nhất trước target_draw
    context = all_draws_before[-window_size:] if len(all_draws_before) >= window_size else all_draws_before
    draw_features = _compute_draw_level_features(context, number_space)
    target_numbers = set(target_draw.numbers)

    features: list[Feature] = []
    for candidate in range(1, number_space + 1):
        # Kiểm tra đã có chưa
        existing = None
        if not overwrite:
            existing = db.execute(
                select(Feature).where(
                    Feature.product_code == target_draw.product_code,
                    Feature.target_draw_id == target_draw.draw_id,
                    Feature.candidate_no == candidate,
                    Feature.window_size == window_size,
                    Feature.feature_version == feature_version,
                )
            ).scalar_one_or_none()

        if existing and not overwrite:
            features.append(existing)
            continue

        cand_features = _compute_candidate_features(candidate, context, window_size, number_space)
        feature_json = {**cand_features, **draw_features}
        label = 1 if candidate in target_numbers else 0

        if existing and overwrite:
            existing.feature_json = feature_json
            existing.label = label
            existing.dataset_role = dataset_role
            db.flush()
            features.append(existing)
        else:
            feat = Feature(
                product_code=target_draw.product_code,
                target_draw_id=target_draw.draw_id,
                candidate_no=candidate,
                window_size=window_size,
                feature_version=feature_version,
                dataset_role=dataset_role,
                feature_json=feature_json,
                label=label,
            )
            db.add(feat)
            db.flush()
            features.append(feat)

    return features


def build_all_features(
    db: Session,
    product_code: str,
    window_size: int = 20,
    feature_version: str = "v1",
    holdout_draws: int = 30,
    number_space: int = 45,
) -> tuple[int, int, int]:
    """Build feature cho tất cả draws của một product.

    Returns:
        (n_train, n_valid, n_test) - số lượng target draws theo role.
    """
    from sqlalchemy import select

    draws = db.execute(
        select(Draw)
        .where(Draw.product_code == product_code)
        .order_by(Draw.draw_no)
    ).scalars().all()

    if len(draws) < window_size + 5:
        logger.warning(f"Không đủ dữ liệu để build features cho {product_code}")
        return 0, 0, 0

    # Time-split: cuối cùng holdout_draws làm test, còn lại chia 80/20 train/valid
    test_draws = draws[-holdout_draws:]
    train_valid_draws = draws[:-holdout_draws]

    n_valid = max(1, len(train_valid_draws) // 5)
    valid_draws = train_valid_draws[-n_valid:]
    train_draws = train_valid_draws[:-n_valid]

    roles = (
        [(d, "train") for d in train_draws]
        + [(d, "valid") for d in valid_draws]
        + [(d, "test") for d in test_draws]
    )

    n_train = n_valid_count = n_test = 0
    for i, (target_draw, role) in enumerate(roles):
        # all draws BEFORE this target (time-safe)
        target_idx = draws.index(target_draw)
        draws_before = draws[:target_idx]

        build_features_for_draw(
            db=db,
            target_draw=target_draw,
            all_draws_before=draws_before,
            window_size=window_size,
            feature_version=feature_version,
            dataset_role=role,
            number_space=number_space,
        )

        if role == "train":
            n_train += 1
        elif role == "valid":
            n_valid_count += 1
        else:
            n_test += 1

        if (i + 1) % 20 == 0:
            db.commit()
            logger.info(f"  ...built {i+1}/{len(roles)} draws")

    db.commit()
    logger.info(f"Feature build xong: train={n_train}, valid={n_valid_count}, test={n_test}")
    return n_train, n_valid_count, n_test


# Thứ tự cố định của feature keys – PHẢI khớp với _compute_candidate_features + _compute_draw_level_features
CANONICAL_FEATURE_KEYS: list[str] = [
    # candidate-level
    "ewma_freq",
    "freq",
    "gap_mean",
    "gap_std",
    "low_high",
    "odd_even",
    "recency",
    "window_size",
    # draw-level
    "window_draw_count",
    "window_entropy",
    "window_low_rate",
    "window_odd_rate",
]


def get_feature_matrix(
    db: Session,
    product_code: str,
    feature_version: str,
    roles: list[str],
    window_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Load feature matrix từ DB, trả (X, y).

    Luôn dùng CANONICAL_FEATURE_KEYS để đảm bảo số chiều ổn định.
    """
    feats = db.execute(
        select(Feature)
        .where(
            Feature.product_code == product_code,
            Feature.feature_version == feature_version,
            Feature.window_size == window_size,
            Feature.dataset_role.in_(roles),
        )
        .order_by(Feature.target_draw_id, Feature.candidate_no)
    ).scalars().all()

    if not feats:
        return np.empty((0, 0)), np.empty(0)

    # Dùng key cố định – bất kể bản ghi đầu có keys nào
    X = np.array(
        [[f.feature_json.get(k, 0.0) for k in CANONICAL_FEATURE_KEYS] for f in feats],
        dtype=np.float32,
    )
    y = np.array([f.label or 0 for f in feats], dtype=np.int32)

    return X, y
