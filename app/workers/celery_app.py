"""Celery application setup."""
from __future__ import annotations

from celery import Celery

from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "vietlott",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.timezone,
    enable_utc=False,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

# ─── Celery Beat Periodic Schedule ───────────────────────────────────────────
celery_app.conf.beat_schedule = {
    # Tự động cào kết quả và train cho Mega 6/45 & Power 6/55 vào 19:15 hàng ngày
    "auto-sync-and-train-main-products-daily": {
        "task": "tasks.learn_from_results",
        "schedule": crontab(hour=19, minute=15),
        "kwargs": {
            "product_codes": ["MEGA_645", "POWER_655"],
            "sync_latest": True,
            "count": 1,
            "force_retrain": False,
        },
    },

}

