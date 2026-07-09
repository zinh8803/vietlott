"""SQLAlchemy database engine and session factory."""
from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


def _build_engine():
    settings = get_settings()
    url = settings.database_url
    kwargs: dict = {}
    if url.startswith("mysql"):
        kwargs = {
            "pool_pre_ping": True,
            "pool_recycle": 3600,
            "echo": settings.debug,
        }
    else:
        kwargs = {"echo": settings.debug, "connect_args": {"check_same_thread": False}}
    return create_engine(url, **kwargs)


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: yields a DB session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist."""
    from app.db import models  # noqa: F401 – import to register mappers
    Base.metadata.create_all(bind=engine)
