"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.main import router
from app.core.config import get_settings
from app.db.database import init_db

logger = logging.getLogger(__name__)
settings = get_settings()


async def _periodic_auto_crawl_and_train():
    """Background task tự động kiểm tra cào kết quả và train định kỳ trong FastAPI."""
    import asyncio
    from datetime import datetime
    while True:
        try:
            await asyncio.sleep(900)  # Kiểm tra mỗi 15 phút
            now = datetime.now()
            # Khung giờ 18:30 - 21:30 hàng ngày là thời gian trả kết quả xổ số
            if 18 <= now.hour <= 21:
                from app.db.database import SessionLocal
                from app.crawlers.vietlott_crawler import sync_draws
                from app.reconcile.reconcile_results import reconcile_pending
                from app.train.auto_retrain import auto_retrain_products_from_results

                db = SessionLocal()
                try:
                    for product in ("MEGA_645", "POWER_655"):
                        sync_draws(db, product, count=1)
                        reconciled = reconcile_pending(db, product)
                        auto_retrain_products_from_results(
                            db,
                            products=[product],
                            reconciled_counts={product: len(reconciled)},
                            force=False,
                        )
                finally:
                    db.close()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"Lỗi background periodic_auto_crawl_and_train: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Khởi tạo DB tables khi start up và chạy background scheduler."""
    import asyncio
    try:
        init_db()
        logger.info("Database initialized OK.")
    except Exception as exc:
        logger.error(f"DB init failed: {exc}")

    bg_task = asyncio.create_task(_periodic_auto_crawl_and_train())
    yield
    bg_task.cancel()



app = FastAPI(
    title="Vietlott AI Prediction System",
    description="ML baseline, LightGBM, XGBoost – candidate-level binary classification.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS: cho phép mọi origin (dev mode) ────────────────────────────────────
# allow_origins=["*"] + allow_credentials=False là cấu hình hợp lệ theo spec
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name, "version": "1.0.0"}
