"""Redis-backed sliding hourly rate limiter."""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.redis_client import get_redis


@dataclass(slots=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int
    current: int


def _hour_bucket(ts: float | None = None) -> int:
    return int((ts if ts is not None else time.time()) // 3600)


def _bucket_key(api_key: str, bucket: int) -> str:
    return f"ratelimit:{api_key}:{bucket}"


def _seconds_until_next_bucket(now: float | None = None) -> int:
    now = now if now is not None else time.time()
    return max(1, 3600 - int(now % 3600))


async def check_and_increment(api_key: str, limit: int) -> RateLimitResult:
    """Atomically increment the request counter for the current hour bucket.

    The counter is set to expire when the bucket rolls over. Calls beyond the
    configured ``limit`` are rejected with ``allowed=False`` and a
    ``retry_after_seconds`` that aligns with the next hour boundary.
    """
    now = time.time()
    bucket = _hour_bucket(now)
    key = _bucket_key(api_key, bucket)
    ttl = _seconds_until_next_bucket(now)

    redis = get_redis()
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, ttl)
    results = await pipe.execute()
    current = int(results[0])

    remaining = max(0, limit - current)
    if current > limit:
        return RateLimitResult(
            allowed=False,
            limit=limit,
            remaining=0,
            retry_after_seconds=ttl,
            current=current,
        )
    return RateLimitResult(
        allowed=True,
        limit=limit,
        remaining=remaining,
        retry_after_seconds=ttl,
        current=current,
    )


async def peek(api_key: str, limit: int) -> RateLimitResult:
    """Return current usage without incrementing."""
    now = time.time()
    bucket = _hour_bucket(now)
    key = _bucket_key(api_key, bucket)
    redis = get_redis()
    raw = await redis.get(key)
    current = int(raw) if raw else 0
    remaining = max(0, limit - current)
    return RateLimitResult(
        allowed=current <= limit,
        limit=limit,
        remaining=remaining,
        retry_after_seconds=_seconds_until_next_bucket(now),
        current=current,
    )
