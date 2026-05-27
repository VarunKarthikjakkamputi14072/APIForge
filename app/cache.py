"""Redis-backed response cache helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from app.redis_client import get_redis


def _params_hash(params: Mapping[str, Any]) -> str:
    normalized = json.dumps(params, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


def cache_key(route: str, params: Mapping[str, Any]) -> str:
    return f"cache:{route}:{_params_hash(params)}"


async def get_cached(route: str, params: Mapping[str, Any]) -> Any | None:
    redis = get_redis()
    raw = await redis.get(cache_key(route, params))
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def set_cached(
    route: str, params: Mapping[str, Any], value: Any, ttl_seconds: int
) -> None:
    redis = get_redis()
    payload = json.dumps(value, default=str, separators=(",", ":"))
    await redis.set(cache_key(route, params), payload, ex=ttl_seconds)
