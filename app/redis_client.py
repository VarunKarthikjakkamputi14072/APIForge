"""Async Redis client factory.

The active client can be overridden (e.g. with `fakeredis`) for tests via
:func:`set_redis_client`. Production use returns a real `redis.asyncio` client
backed by ``settings.redis_url``.
"""

from __future__ import annotations

from typing import Optional

import redis.asyncio as redis_asyncio

from app.config import get_settings

_client: Optional[redis_asyncio.Redis] = None


def get_redis() -> redis_asyncio.Redis:
    """Return the process-wide Redis client, creating it on first use."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = redis_asyncio.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _client


def set_redis_client(client: redis_asyncio.Redis) -> None:
    """Override the process-wide Redis client (intended for tests)."""
    global _client
    _client = client


async def close_redis() -> None:
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:  # pragma: no cover - best-effort cleanup
            pass
        _client = None
