"""SQLAlchemy ORM models matching the schema in docs.txt."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.mysql import BIGINT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Draw(Base):
    """Kết quả kỳ quay chuẩn hóa."""

    __tablename__ = "draws"

    draw_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    product_code: Mapped[str] = mapped_column(String(32), nullable=False)
    draw_no: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    draw_date: Mapped[date] = mapped_column(Date, nullable=False)
    open_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    n1: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    n2: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    n3: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    n4: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    n5: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    n6: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    bonus_number: Mapped[Optional[int]] = mapped_column(TINYINT(unsigned=True), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    features: Mapped[list["Feature"]] = relationship(back_populates="target_draw")

    __table_args__ = (
        Index("uk_draw_product_no", "product_code", "draw_no", unique=True),
        Index("idx_draw_product_date", "product_code", "draw_date"),
    )

    @property
    def numbers(self) -> list[int]:
        return [self.n1, self.n2, self.n3, self.n4, self.n5, self.n6]


class Feature(Base):
    """Feature cache ở mức candidate / target_draw."""

    __tablename__ = "features"

    feature_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    product_code: Mapped[str] = mapped_column(String(32), nullable=False)
    target_draw_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), ForeignKey("draws.draw_id"), nullable=False
    )
    candidate_no: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    window_size: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    feature_version: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_role: Mapped[str] = mapped_column(String(16), nullable=False)  # train/valid/test
    feature_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    feature_uri: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    label: Mapped[Optional[int]] = mapped_column(TINYINT(1), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    target_draw: Mapped["Draw"] = relationship(back_populates="features")

    __table_args__ = (
        Index(
            "uk_feature_sample",
            "product_code",
            "target_draw_id",
            "candidate_no",
            "window_size",
            "feature_version",
            unique=True,
        ),
        Index("idx_feature_lookup", "product_code", "feature_version", "dataset_role"),
    )


class Model(Base):
    """Metadata model / version."""

    __tablename__ = "models"

    model_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    product_code: Mapped[str] = mapped_column(String(32), nullable=False)
    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    feature_version: Mapped[str] = mapped_column(String(64), nullable=False)
    window_size: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    train_from_draw_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    train_to_draw_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    valid_from_draw_id: Mapped[Optional[int]] = mapped_column(BIGINT(unsigned=True), nullable=True)
    valid_to_draw_id: Mapped[Optional[int]] = mapped_column(BIGINT(unsigned=True), nullable=True)
    hyperparams_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    metrics_summary_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    artifact_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    model_checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    framework_versions_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="challenger")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    promoted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)

    predictions: Mapped[list["Prediction"]] = relationship(back_populates="model")
    metrics: Mapped[list["Metric"]] = relationship(back_populates="model")

    __table_args__ = (
        Index("idx_model_product_status", "product_code", "status"),
        Index("idx_model_algo", "algorithm"),
    )


class Prediction(Base):
    """Lưu lần sinh dự đoán."""

    __tablename__ = "predictions"

    prediction_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    model_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), ForeignKey("models.model_id"), nullable=False
    )
    product_code: Mapped[str] = mapped_column(String(32), nullable=False)
    as_of_draw_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), ForeignKey("draws.draw_id"), nullable=False
    )
    predicted_draw_no: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    predicted_draw_date: Mapped[date] = mapped_column(Date, nullable=False)
    probabilities_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    top6_json: Mapped[list] = mapped_column(JSON, nullable=False)
    actual_top6_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    actual_bonus_number: Mapped[Optional[int]] = mapped_column(TINYINT(unsigned=True), nullable=True)
    hit_count_main: Mapped[Optional[int]] = mapped_column(TINYINT(unsigned=True), nullable=True)
    hit_bonus: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    request_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending_result")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    reconciled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)

    model: Mapped["Model"] = relationship(back_populates="predictions")

    __table_args__ = (
        Index(
            "uk_prediction_once",
            "model_id",
            "product_code",
            "predicted_draw_no",
            "request_type",
            unique=True,
        ),
        Index("idx_prediction_pending", "product_code", "status", "predicted_draw_date"),
    )


class AppUser(Base):
    """Simple local user/admin account for daily ticket quotas."""

    __tablename__ = "app_users"

    user_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    password_hash: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    daily_ticket_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    lock_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    tickets: Mapped[list["UserTicket"]] = relationship(back_populates="user")

    __table_args__ = (
        Index("idx_app_user_role", "role"),
    )


class UserTicket(Base):
    """A ticket generated by a user/admin from a prediction."""

    __tablename__ = "user_tickets"

    ticket_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), ForeignKey("app_users.user_id"), nullable=False
    )
    prediction_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), ForeignKey("predictions.prediction_id"), nullable=False
    )
    product_code: Mapped[str] = mapped_column(String(32), nullable=False)
    predicted_draw_no: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    numbers_json: Mapped[list] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    user: Mapped["AppUser"] = relationship(back_populates="tickets")

    __table_args__ = (
        Index("idx_ticket_user_date", "user_id", "created_at"),
        Index("idx_ticket_product_draw", "product_code", "predicted_draw_no"),
    )


class Metric(Base):
    """Lưu metric holdout / backtest / live."""

    __tablename__ = "metrics"

    metric_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    model_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), ForeignKey("models.model_id"), nullable=False
    )
    product_code: Mapped[str] = mapped_column(String(32), nullable=False)
    eval_scope: Mapped[str] = mapped_column(String(32), nullable=False)
    fold_no: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    period_from_draw_id: Mapped[Optional[int]] = mapped_column(BIGINT(unsigned=True), nullable=True)
    period_to_draw_id: Mapped[Optional[int]] = mapped_column(BIGINT(unsigned=True), nullable=True)
    precision_at_6: Mapped[Optional[float]] = mapped_column(nullable=True)
    top_k_accuracy: Mapped[Optional[float]] = mapped_column(nullable=True)
    log_loss: Mapped[Optional[float]] = mapped_column(nullable=True)
    brier_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    metric_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    model: Mapped["Model"] = relationship(back_populates="metrics")

    __table_args__ = (Index("idx_metrics_model_scope", "model_id", "eval_scope"),)


class RetrainJob(Base):
    """Quản lý job retrain."""

    __tablename__ = "retrain_jobs"

    job_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    product_code: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_reason: Mapped[str] = mapped_column(String(128), nullable=False)
    request_payload_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    best_model_id: Mapped[Optional[int]] = mapped_column(
        BIGINT(unsigned=True), ForeignKey("models.model_id"), nullable=True
    )
    log_uri: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_retrain_status", "product_code", "status", "created_at"),
    )
