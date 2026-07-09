"""Application configuration using Pydantic Settings + YAML."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "vietlott-ml"
    debug: bool = False
    timezone: str = "Asia/Ho_Chi_Minh"

    # Database
    database_url: str = "mysql+pymysql://root:password@localhost:3306/vietlott_ml"

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # Storage
    artifact_root: str = "./artifacts"

    # Products config (loaded from YAML)
    products: dict[str, Any] = {}
    training: dict[str, Any] = {}
    scheduler: dict[str, Any] = {}

    def model_post_init(self, __context: Any) -> None:  # noqa: ANN401
        config_path = Path(__file__).parent / "config.yaml"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f) or {}
            # Merge YAML into settings (YAML doesn't override env vars)
            if not self.products:
                object.__setattr__(self, "products", yaml_data.get("products", {}))
            if not self.training:
                object.__setattr__(self, "training", yaml_data.get("training", {}))
            if not self.scheduler:
                object.__setattr__(self, "scheduler", yaml_data.get("scheduler", {}))


@lru_cache
def get_settings() -> Settings:
    return Settings()
