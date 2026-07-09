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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Khởi tạo DB tables khi start up."""
    try:
        init_db()
        logger.info("Database initialized OK.")
    except Exception as exc:
        logger.error(f"DB init failed: {exc}")
    yield


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
