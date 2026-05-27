"""Custom middleware: rate limiting + request logging.

The middleware only enforces rate limits / logs requests for `/api/*` routes,
which require an API key. Auth and meta routes pass through untouched.
"""

from __future__ import annotations

import json
import time
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.database import SessionLocal
from app.deps import get_rate_limit_for_tier
from app.models import APIKey, Developer, RequestLog
from app.rate_limit import check_and_increment
from app.security import API_KEY_PREFIX, hash_api_key
from app.config import get_settings


def _safe_query_params(request: Request) -> dict[str, Any]:
    try:
        return dict(request.query_params)
    except Exception:
        return {}


class APIKeyRateLimitAndLogMiddleware(BaseHTTPMiddleware):
    """Enforce rate limits and persist a `RequestLog` for every `/api/*` call.

    The middleware runs *before* route handlers, so it must look up the API key
    itself. The actual route handler still validates the API key via the
    `require_api_key` dependency — the two layers are intentionally independent.
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
            settings = get_settings()
            db = SessionLocal()
            try:
                key_hash = hash_api_key(api_key_header)
                api_key_row = (
                    db.query(APIKey).filter(APIKey.key_hash == key_hash).one_or_none()
                )
                if api_key_row is not None and api_key_row.is_active:
                    developer = db.get(Developer, api_key_row.developer_id)
                    tier = developer.tier if developer else "free"
                    default_limit = (
                        settings.pro_tier_requests_per_hour
                        if tier == "pro"
                        else settings.free_tier_requests_per_hour
                    )
                    limit = get_rate_limit_for_tier(db, tier, default_limit)
            finally:
                db.close()

        rate_headers: dict[str, str] = {}
        if api_key_row is not None and limit is not None:
            result = await check_and_increment(api_key_header, limit)
            rate_headers["X-RateLimit-Limit"] = str(result.limit)
            rate_headers["X-RateLimit-Remaining"] = str(result.remaining)
            rate_headers["X-RateLimit-Reset"] = str(result.retry_after_seconds)
            if not result.allowed:
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
                # Log the 429 too so analytics reflect throttled traffic.
                self._persist_log(
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
            self._persist_log(
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

        self._persist_log(
            api_key_id=api_key_row.id if api_key_row else None,
            endpoint=request.url.path,
            params=_safe_query_params(request),
            response_time_ms=duration_ms,
            status_code=response.status_code,
            upstream_latency_ms=getattr(request.state, "upstream_latency_ms", None),
        )
        return response

    @staticmethod
    def _persist_log(
        *,
        api_key_id: int | None,
        endpoint: str,
        params: dict[str, Any],
        response_time_ms: int,
        status_code: int,
        upstream_latency_ms: int | None,
    ) -> None:
        db = SessionLocal()
        try:
            log = RequestLog(
                api_key_id=api_key_id,
                endpoint=endpoint,
                # SQLite + JSON column happily takes a dict; serialize defensively.
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
