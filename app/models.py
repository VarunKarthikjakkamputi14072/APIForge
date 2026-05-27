"""SQLAlchemy ORM models for APIForge."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Developer(Base):
    __tablename__ = "developers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    tier: Mapped[str] = mapped_column(String(32), default="free", nullable=False)

    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey", back_populates="developer", cascade="all, delete-orphan"
    )


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    developer_id: Mapped[int] = mapped_column(
        ForeignKey("developers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    # First few chars of the key for display in dashboards (e.g. "af_a1b2…").
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    developer: Mapped[Developer] = relationship("Developer", back_populates="api_keys")
    request_logs: Mapped[list["RequestLog"]] = relationship(
        "RequestLog", back_populates="api_key", cascade="all, delete-orphan"
    )


class RequestLog(Base):
    __tablename__ = "request_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    api_key_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True, index=True
    )
    endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    upstream_latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    api_key: Mapped[Optional[APIKey]] = relationship("APIKey", back_populates="request_logs")


class RateLimitConfig(Base):
    __tablename__ = "rate_limit_config"
    __table_args__ = (UniqueConstraint("tier", name="uq_rate_limit_tier"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tier: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    requests_per_hour: Mapped[int] = mapped_column(Integer, nullable=False)
