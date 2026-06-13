"""FastAPI dependencies."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import APIKey, Developer, RateLimitConfig
from app.security import API_KEY_PREFIX, hash_api_key


def _extract_key(x_api_key: str | None, authorization: str | None) -> str | None:
    """Read the Transit key from either header.

    Accepting `Authorization: Bearer af_...` (in addition to `X-API-Key`) makes
    Transit a true drop-in for any OpenAI-compatible client — point the client's
    base_url at Transit and pass an `af_` key as its API key, no other changes.
    """
    if x_api_key and x_api_key.startswith(API_KEY_PREFIX):
        return x_api_key
    if authorization:
        token = authorization[7:] if authorization.lower().startswith("bearer ") else authorization
        if token.startswith(API_KEY_PREFIX):
            return token
    return None


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> APIKey:
    """Resolve the active :class:`APIKey` from `X-API-Key` or `Authorization: Bearer`.

    Raises 401 when the key is missing/invalid or has been disabled.
    """
    key = _extract_key(x_api_key, authorization)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed API key (X-API-Key or Authorization: Bearer).",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_hash = hash_api_key(key)
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
