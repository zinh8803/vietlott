"""Script xóa dữ liệu ảo và crawl 150 kỳ quay thực tế từ vietlott.vn cho cả 2 sản phẩm."""
from __future__ import annotations

import os
import sys
from loguru import logger

# Thêm project root vào sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal, engine
from app.crawlers.vietlott_crawler import sync_draws

def main():
    logger.info("=== BẮT ĐẦU DỌN DẸP DỮ LIỆU ẢO & CRAWL DỮ LIỆU THẬT ===")
    
    db = SessionLocal()
    try:
        # Xóa các dữ liệu cũ trong DB để loại bỏ hoàn toàn dữ liệu ảo (theo thứ tự FK)
        logger.info("Xóa dữ liệu cũ trong các bảng liên quan...")
        db.execute(engine.utility.text("SET FOREIGN_KEY_CHECKS = 0;"))
        db.execute(engine.utility.text("TRUNCATE TABLE metrics;"))
        db.execute(engine.utility.text("TRUNCATE TABLE predictions;"))
        db.execute(engine.utility.text("TRUNCATE TABLE features;"))
        db.execute(engine.utility.text("TRUNCATE TABLE draws;"))
        db.execute(engine.utility.text("TRUNCATE TABLE models;"))
        db.execute(engine.utility.text("TRUNCATE TABLE retrain_jobs;"))
        db.execute(engine.utility.text("SET FOREIGN_KEY_CHECKS = 1;"))
        db.commit()
        logger.info("Đã xóa toàn bộ dữ liệu ảo cũ.")
        
        # Crawl 150 kỳ quay thực tế từ Vietlott cho MEGA_645
        logger.info("Crawl 150 kỳ quay thực tế cho MEGA 6/45...")
        mega_draws = sync_draws(db, "MEGA_645", count=150, force=True)
        logger.info(f"Hoàn thành! Đã nạp {len(mega_draws)} kỳ quay MEGA 6/45 thực tế.")
        
        # Crawl 150 kỳ quay thực tế từ Vietlott cho POWER_655
        logger.info("Crawl 150 kỳ quay thực tế cho POWER 6/55...")
        power_draws = sync_draws(db, "POWER_655", count=150, force=True)
        logger.info(f"Hoàn thành! Đã nạp {len(power_draws)} kỳ quay POWER 6/55 thực tế.")
        
        logger.info("=== HOÀN THÀNH ĐỒNG BỘ DỮ LIỆU THẬT! ===")
    except Exception as e:
        logger.error(f"Lỗi trong quá trình thực hiện: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Sửa lỗi import text từ sqlalchemy
    import sqlalchemy
    # Khắc phục lỗi sqlalchemy text
    from sqlalchemy import text
    # Thay thế hàm execute
    db = SessionLocal()
    try:
        logger.info("Xóa dữ liệu cũ trong các bảng liên quan...")
        db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        db.execute(text("TRUNCATE TABLE metrics;"))
        db.execute(text("TRUNCATE TABLE predictions;"))
        db.execute(text("TRUNCATE TABLE features;"))
        db.execute(text("TRUNCATE TABLE draws;"))
        db.execute(text("TRUNCATE TABLE models;"))
        db.execute(text("TRUNCATE TABLE retrain_jobs;"))
        db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        db.commit()
        logger.info("Đã dọn dẹp DB.")
        
        logger.info("Crawl 150 kỳ quay thực tế cho MEGA 6/45...")
        mega_draws = sync_draws(db, "MEGA_645", count=150, force=True)
        logger.info(f"Thành công MEGA 6/45: {len(mega_draws)} kỳ.")
        
        logger.info("Crawl 150 kỳ quay thực tế cho POWER 6/55...")
        power_draws = sync_draws(db, "POWER_655", count=150, force=True)
        logger.info(f"Thành công POWER 6/55: {len(power_draws)} kỳ.")
        
        logger.info("=== HOÀN THÀNH ===")
    except Exception as e:
        logger.exception(f"Lỗi: {e}")
        db.rollback()
    finally:
        db.close()
