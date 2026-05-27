"""FastAPI dependencies."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import APIKey, Developer, RateLimitConfig
from app.security import API_KEY_PREFIX, hash_api_key


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> APIKey:
    """Resolve the active :class:`APIKey` from the `X-API-Key` header.

    Raises 401 when the header is missing/invalid or the key has been disabled.
    """
    if not x_api_key or not x_api_key.startswith(API_KEY_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_hash = hash_api_key(x_api_key)
    api_key = db.execute(
        select(APIKey).where(APIKey.key_hash == key_hash)
    ).scalar_one_or_none()
    if api_key is None or not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return api_key


def get_developer_for_api_key(
    api_key: APIKey = Depends(require_api_key),
    db: Session = Depends(get_db),
) -> Developer:
    developer = db.get(Developer, api_key.developer_id)
    if developer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Owning developer no longer exists.",
        )
    return developer


def get_rate_limit_for_tier(db: Session, tier: str, default: int) -> int:
    cfg = db.execute(
        select(RateLimitConfig).where(RateLimitConfig.tier == tier)
    ).scalar_one_or_none()
    return cfg.requests_per_hour if cfg else default
