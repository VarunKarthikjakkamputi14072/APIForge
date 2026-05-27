"""SQLAlchemy engine, session, and base."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _build_engine(database_url: str) -> Engine:
    connect_args: dict = {}
    if database_url.startswith("sqlite"):
        # Needed when used across threads (e.g. TestClient + background tasks).
        connect_args["check_same_thread"] = False
    return create_engine(database_url, future=True, connect_args=connect_args)


settings = get_settings()
engine: Engine = _build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Used for tests / first-time bootstrapping."""
    # Importing models registers them with `Base.metadata`.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
