"""Shared HTTPX client utilities for upstream API calls."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import httpx

from app.config import get_settings


class UpstreamError(Exception):
    """Raised when an upstream call fails after normalization attempts."""

    def __init__(self, message: str, *, status_code: int = 502, provider: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.provider = provider


@dataclass(slots=True)
class TimedResponse:
    """An upstream HTTP response paired with the latency we observed."""

    response: httpx.Response
    latency_ms: int


_shared_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """Return a lazily-initialized process-wide async HTTP client."""
    global _shared_client
    if _shared_client is None:
        settings = get_settings()
        _shared_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.upstream_timeout_seconds),
            headers={"User-Agent": "APIForge/0.1"},
        )
    return _shared_client


def set_http_client(client: httpx.AsyncClient) -> None:
    """Override the shared HTTP client (intended for tests)."""
    global _shared_client
    _shared_client = client


async def close_http_client() -> None:
    global _shared_client
    if _shared_client is not None:
        try:
            await _shared_client.aclose()
        except Exception:  # pragma: no cover
            pass
        _shared_client = None


@asynccontextmanager
async def timed_get(
    url: str, *, params: dict | None = None, provider: str
) -> AsyncIterator[TimedResponse]:
    """Async context manager that performs a GET and records latency."""
    client = get_http_client()
    start = time.perf_counter()
    try:
        response = await client.get(url, params=params)
    except httpx.HTTPError as exc:
        raise UpstreamError(
            f"{provider} request failed: {exc}", status_code=504, provider=provider
        ) from exc
    latency_ms = int((time.perf_counter() - start) * 1000)
    yield TimedResponse(response=response, latency_ms=latency_ms)
