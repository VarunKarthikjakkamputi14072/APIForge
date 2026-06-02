"""Custom middleware: rate limiting + request logging.

The middleware only enforces rate limits / logs requests for `/api/*` routes,
which require an API key. Auth and meta routes pass through untouched.
"""

from __future__ import annotations

import asyncio
import functools
import json
import time
from typing import Any

from fastapi import Request, Response
from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.database import SessionLocal
from app.deps import get_rate_limit_for_tier
from app.models import APIKey, Developer, RequestLog
from app.rate_limit import check_and_increment
from app.redis_client import get_redis
from app.security import API_KEY_PREFIX, hash_api_key
from app.config import get_settings

# Cache TTL for key→tier lookups. Short enough that revoked keys stop working
# within a minute; long enough that the DB is not hit on every request.
_KEY_TIER_CACHE_TTL = 60  # seconds


async def _get_tier_cached(key_hash: str) -> str | None:
    """Return the tier for a key hash from Redis cache, or None on miss."""
    redis = get_redis()
    try:
        return await redis.get(f"keytier:{key_hash}")
    except Exception:
        return None


async def _set_tier_cached(key_hash: str, tier: str) -> None:
    redis = get_redis()
    try:
        await redis.set(f"keytier:{key_hash}", tier, ex=_KEY_TIER_CACHE_TTL)
    except Exception:
        pass


def _safe_query_params(request: Request) -> dict[str, Any]:
    try:
        return dict(request.query_params)
    except Exception:
        return {}


def _lookup_key_sync(key_hash: str) -> tuple[APIKey | None, str | None]:
    """Synchronous DB lookup — runs in a thread pool, never on the event loop."""
    db = SessionLocal()
    try:
        api_key_row = db.query(APIKey).filter(APIKey.key_hash == key_hash).one_or_none()
        if api_key_row is None or not api_key_row.is_active:
            return None, None
        developer = db.get(Developer, api_key_row.developer_id)
        tier = developer.tier if developer else "free"
        return api_key_row, tier
    finally:
        db.close()


def _lookup_key_id_sync(key_hash: str) -> APIKey | None:
    """Lightweight key-id-only lookup for when tier is already cached."""
    db = SessionLocal()
    try:
        return db.query(APIKey).filter(APIKey.key_hash == key_hash).one_or_none()
    finally:
        db.close()


@functools.lru_cache(maxsize=128)
def _get_rate_limit_sync(tier: str) -> int:
    """Read rate limit config from DB — runs in thread pool."""
    settings = get_settings()
    db = SessionLocal()
    try:
        default = (
            settings.pro_tier_requests_per_hour
            if tier == "pro"
            else settings.free_tier_requests_per_hour
        )
        return get_rate_limit_for_tier(db, tier, default)
    finally:
        db.close()


def _write_log_sync(
    *,
    api_key_id: int | None,
    endpoint: str,
    params: dict[str, Any],
    response_time_ms: int,
    status_code: int,
    upstream_latency_ms: int | None,
) -> None:
    """Write a RequestLog row — runs in thread pool, fire-and-forget."""
    db = SessionLocal()
    try:
        log = RequestLog(
            api_key_id=api_key_id,
            endpoint=endpoint,
            params=json.loads(json.dumps(params, default=str)),
            response_time_ms=response_time_ms,
            status_code=status_code,
            upstream_latency_ms=upstream_latency_ms,
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


class APIKeyRateLimitAndLogMiddleware(BaseHTTPMiddleware):
    """Enforce rate limits and persist a RequestLog for every /api/* call.

    All synchronous DB work runs in asyncio.to_thread() so the event loop
    is never blocked. Request logging is fire-and-forget (create_task) so
    it doesn't add to response latency at all.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        api_key_header = request.headers.get("X-API-Key", "")
        api_key_row: APIKey | None = None
        limit: int | None = None

        if api_key_header and api_key_header.startswith(API_KEY_PREFIX):
            key_hash = hash_api_key(api_key_header)

            cached_tier = await _get_tier_cached(key_hash)
            if cached_tier is not None:
                # Tier known — only need the key row for the log ID.
                api_key_row = await asyncio.to_thread(_lookup_key_id_sync, key_hash)
                if api_key_row is not None and api_key_row.is_active:
                    limit = await asyncio.to_thread(_get_rate_limit_sync, cached_tier)
            else:
                # Full lookup — also caches tier for future requests.
                api_key_row, tier = await asyncio.to_thread(_lookup_key_sync, key_hash)
                if api_key_row is not None and tier is not None:
                    await _set_tier_cached(key_hash, tier)
                    limit = await asyncio.to_thread(_get_rate_limit_sync, tier)

        rate_headers: dict[str, str] = {}
        if api_key_row is not None and limit is not None:
            try:
                result = await check_and_increment(api_key_header, limit)
            except RedisError:
                # Fail open: if Redis is unreachable we must not 500 the whole
                # gateway. Skip rate limiting for this request and let it through.
                # A brief Redis outage degrades to "no limiting" rather than a
                # total outage; the request is still served and logged.
                result = None
            if result is not None:
                rate_headers["X-RateLimit-Limit"] = str(result.limit)
                rate_headers["X-RateLimit-Remaining"] = str(result.remaining)
                rate_headers["X-RateLimit-Reset"] = str(result.retry_after_seconds)
            if result is not None and not result.allowed:
                body = {
                    "error": "rate_limit_exceeded",
                    "detail": (
                        f"Rate limit of {result.limit} requests/hour exceeded "
                        f"for this API key."
                    ),
                    "retry_after_seconds": result.retry_after_seconds,
                }
                response = JSONResponse(status_code=429, content=body)
                response.headers["Retry-After"] = str(result.retry_after_seconds)
                for k, v in rate_headers.items():
                    response.headers[k] = v
                self._fire_log(
                    api_key_id=api_key_row.id,
                    endpoint=request.url.path,
                    params=_safe_query_params(request),
                    response_time_ms=0,
                    status_code=429,
                    upstream_latency_ms=0,
                )
                return response

        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - start) * 1000)
            self._fire_log(
                api_key_id=api_key_row.id if api_key_row else None,
                endpoint=request.url.path,
                params=_safe_query_params(request),
                response_time_ms=duration_ms,
                status_code=500,
                upstream_latency_ms=getattr(request.state, "upstream_latency_ms", None),
            )
            raise

        duration_ms = int((time.perf_counter() - start) * 1000)

        for k, v in rate_headers.items():
            response.headers[k] = v

        self._fire_log(
            api_key_id=api_key_row.id if api_key_row else None,
            endpoint=request.url.path,
            params=_safe_query_params(request),
            response_time_ms=duration_ms,
            status_code=response.status_code,
            upstream_latency_ms=getattr(request.state, "upstream_latency_ms", None),
        )
        return response

    @staticmethod
    def _fire_log(**kwargs: Any) -> None:
        """Schedule log write as a background task — doesn't block the response."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(asyncio.to_thread(_write_log_sync, **kwargs))
        except RuntimeError:
            # No running loop (e.g. during tests) — write synchronously.
            _write_log_sync(**kwargs)
