"""Tests for the Redis-backed rate limiter and middleware integration."""

from __future__ import annotations

import asyncio

import pytest

from app.rate_limit import check_and_increment, peek


@pytest.mark.asyncio
async def test_check_and_increment_increments_until_limit(fake_redis):
    key = "af_test_key"
    for i in range(1, 4):
        result = await check_and_increment(key, limit=3)
        assert result.allowed is True
        assert result.current == i
        assert result.remaining == 3 - i

    rejected = await check_and_increment(key, limit=3)
    assert rejected.allowed is False
    assert rejected.remaining == 0
    assert rejected.retry_after_seconds > 0


@pytest.mark.asyncio
async def test_peek_does_not_increment(fake_redis):
    key = "af_peek_key"
    await check_and_increment(key, limit=10)
    snapshot1 = await peek(key, limit=10)
    snapshot2 = await peek(key, limit=10)
    assert snapshot1.current == 1
    assert snapshot2.current == 1


def test_middleware_returns_429_after_exceeding_limit(
    client, registered_developer, monkeypatch
):
    _, _, api_key = registered_developer

    async def fake_fetch_weather(city: str):
        from datetime import datetime, timezone

        from app.schemas import WeatherResponse

        return (
            WeatherResponse(
                city=city,
                temperature_c=10.0,
                humidity_pct=50.0,
                condition="Cloudy",
                wind_kph=5.0,
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            ),
            10,
        )

    monkeypatch.setattr("app.routers.gateway.fetch_weather", fake_fetch_weather)

    headers = {"X-API-Key": api_key}
    # FREE_TIER_REQUESTS_PER_HOUR is set to 5 in tests/conftest.py
    statuses = []
    for _ in range(6):
        r = client.get("/api/weather/Berlin", headers=headers)
        statuses.append(r.status_code)

    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429

    # Limit-exhausted request must include rate-limit + Retry-After headers
    last = client.get("/api/weather/Berlin", headers=headers)
    assert last.status_code == 429
    body = last.json()
    assert body["error"] == "rate_limit_exceeded"
    assert body["retry_after_seconds"] > 0
    assert int(last.headers["X-RateLimit-Limit"]) == 5
    assert int(last.headers["X-RateLimit-Remaining"]) == 0
    assert int(last.headers["Retry-After"]) > 0


def test_rate_limit_headers_present_on_successful_response(
    client, registered_developer, monkeypatch
):
    _, _, api_key = registered_developer

    async def fake_fetch_quote(symbol: str):
        from datetime import datetime, timezone

        from app.schemas import FinanceQuoteResponse

        return (
            FinanceQuoteResponse(
                symbol=symbol.upper(),
                price=1.0,
                change_pct=0.0,
                volume=0,
                market_cap=None,
                timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            ),
            5,
        )

    monkeypatch.setattr("app.routers.gateway.fetch_quote", fake_fetch_quote)

    response = client.get(
        "/api/finance/quote",
        params={"symbol": "msft"},
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
