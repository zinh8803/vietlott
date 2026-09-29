"""Script chạy Crontab định kỳ tự động cào kết quả mới và train mô hình cho Mega 6/45 và Power 6/55."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Thêm thư mục gốc dự án vào sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from loguru import logger
from app.db.database import SessionLocal
from app.reconcile.reconcile_results import reconcile_pending
from app.crawlers.vietlott_crawler import sync_draws
from app.train.auto_retrain import auto_retrain_products_from_results

def main():
    logger.info("=== [CRON] Bắt đầu tự động cào dữ liệu & retrain cho Mega 6/45 và Power 6/55 ===")
    db = SessionLocal()
    products = ["MEGA_645", "POWER_655"]
    
    synced_counts: dict[str, int] = {}
    reconciled_counts: dict[str, int] = {}
    
    try:
        # 1. Sync/crawl kết quả chính thức mới nhất từ vietlott.vn
        for product in products:
            logger.info(f"[CRON] Kiểm tra và cào kết quả mới nhất cho {product}...")
            draws = sync_draws(db, product, count=1)
            synced_counts[product] = len(draws)
            logger.info(f"[CRON] {product}: Cào được {len(draws)} kỳ quay.")
            
        # 2. Đối chiếu các vé/dự đoán AI chưa có kết quả
        for product in products:
            reconciled = reconcile_pending(db, product)
            reconciled_counts[product] = len(reconciled)
            logger.info(f"[CRON] {product}: Đã đối chiếu {len(reconciled)} dự đoán.")
            
        # 3. Tự động retrain nếu có kết quả mới hoặc đủ kỳ quay mới
        results = auto_retrain_products_from_results(
            db,
            products=products,
            reconciled_counts=reconciled_counts,
            force=False,
        )
        
        for product, res in results.items():
            status = res.get("status")
            if status == "trained":
                logger.info(f"[CRON] {product} RETRAIN THÀNH CÔNG -> Champion Model ID: #{res.get('champion_model_id')}")
            else:
                logger.info(f"[CRON] {product} SKIPPED: {res.get('reason')}")
                
        logger.info("=== [CRON] Hoàn thành luồng tự động cào và train ===")
    except Exception as e:
        logger.error(f"[CRON] Lỗi trong quá trình chạy tự động: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
