"""Script khởi tạo database và seed dữ liệu mẫu."""
from __future__ import annotations

import sys

from loguru import logger

# Thêm project root vào sys.path
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.database import init_db, SessionLocal
from app.crawlers.vietlott_crawler import seed_sample_draws


def main():
    logger.info("=== Khởi tạo database ===")
    init_db()
    logger.info("Tạo tables thành công.")

    db = SessionLocal()
    try:
        logger.info("=== Seed dữ liệu mẫu ===")
        mega_draws = seed_sample_draws(db, "MEGA_645", count=550)
        logger.info(f"Mega 6/45: {len(mega_draws)} draws")

        power_draws = seed_sample_draws(db, "POWER_655", count=550)
        logger.info(f"Power 6/55: {len(power_draws)} draws")

        logger.info("=== Seed hoàn thành! ===")
    finally:
        db.close()


if __name__ == "__main__":
    main()
