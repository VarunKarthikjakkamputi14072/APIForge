"""Tests for /api/* gateway routes (with mocked upstream calls)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.schemas import FinanceQuoteResponse, NewsArticle, NewsResponse, WeatherResponse


def _weather_fixture(city: str = "Berlin") -> WeatherResponse:
    return WeatherResponse(
        city=city,
        temperature_c=21.5,
        humidity_pct=55.0,
        condition="Clear",
        wind_kph=12.6,
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _news_fixture(topic: str = "tech") -> NewsResponse:
    return NewsResponse(
        articles=[
            NewsArticle(
                title="Big launch",
                summary="A summary.",
                source="TestWire",
                url="https://example.com/a",
                published_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
            )
        ],
        total=1,
        topic=topic,
    )


def _finance_fixture(symbol: str = "AAPL") -> FinanceQuoteResponse:
    return FinanceQuoteResponse(
        symbol=symbol,
        price=189.42,
        change_pct=1.23,
        volume=1_234_567,
        market_cap=None,
        timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


# --- Auth enforcement --------------------------------------------------------


def test_weather_without_api_key_is_401(client):
    response = client.get("/api/weather/Berlin")
    assert response.status_code == 401


def test_weather_with_bad_api_key_is_401(client):
    response = client.get("/api/weather/Berlin", headers={"X-API-Key": "af_bogus"})
    assert response.status_code == 401


# --- Weather route -----------------------------------------------------------


def test_weather_route_normalizes_and_caches(client, registered_developer, monkeypatch):
    _, _, api_key = registered_developer
    call_count = {"n": 0}

    async def fake_fetch_weather(city: str):
        call_count["n"] += 1
        return _weather_fixture(city), 42

    monkeypatch.setattr(
        "app.routers.gateway.fetch_weather", fake_fetch_weather
    )

    headers = {"X-API-Key": api_key}
    r1 = client.get("/api/weather/Berlin", headers=headers)
    assert r1.status_code == 200
    body = r1.json()
    assert set(body.keys()) == {
        "city",
        "temperature_c",
        "humidity_pct",
        "condition",
        "wind_kph",
        "timestamp",
    }
    assert body["city"] == "Berlin"
    assert "X-RateLimit-Remaining" in r1.headers

    # Second call should hit cache and not invoke the upstream client again.
    r2 = client.get("/api/weather/Berlin", headers=headers)
    assert r2.status_code == 200
    assert call_count["n"] == 1


# --- News route --------------------------------------------------------------


def test_news_route_normalizes(client, registered_developer, monkeypatch):
    _, _, api_key = registered_developer

    async def fake_fetch_news(topic: str, limit: int):
        return _news_fixture(topic), 30

    monkeypatch.setattr("app.routers.gateway.fetch_news", fake_fetch_news)

    response = client.get(
        "/api/news",
        params={"topic": "ai", "limit": 3},
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["topic"] == "ai"
    assert body["total"] == 1
    assert body["articles"][0]["source"] == "TestWire"


# --- Finance route -----------------------------------------------------------


def test_finance_route_normalizes(client, registered_developer, monkeypatch):
    _, _, api_key = registered_developer

    async def fake_fetch_quote(symbol: str):
        return _finance_fixture(symbol.upper()), 25

    monkeypatch.setattr("app.routers.gateway.fetch_quote", fake_fetch_quote)

    response = client.get(
        "/api/finance/quote",
        params={"symbol": "aapl"},
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "AAPL"
    assert body["price"] == pytest.approx(189.42)
    assert body["change_pct"] == pytest.approx(1.23)


# --- Aggregate route ---------------------------------------------------------


def test_aggregate_combines_weather_and_news(client, registered_developer, monkeypatch):
    _, _, api_key = registered_developer

    async def fake_fetch_weather(city: str):
        return _weather_fixture(city), 40

    async def fake_fetch_news(topic: str, limit: int):
        return _news_fixture(topic), 35

    monkeypatch.setattr("app.routers.gateway.fetch_weather", fake_fetch_weather)
    monkeypatch.setattr("app.routers.gateway.fetch_news", fake_fetch_news)

    response = client.get(
        "/api/aggregate",
        params={"city": "Berlin", "topic": "ai", "limit": 2},
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["weather"]["city"] == "Berlin"
    assert body["news"]["topic"] == "ai"
    assert body["errors"] == {}


def test_aggregate_partial_failure_returns_errors(
    client, registered_developer, monkeypatch
):
    _, _, api_key = registered_developer
    from app.upstream.base import UpstreamError

    async def fake_fetch_weather(city: str):
        return _weather_fixture(city), 40

    async def failing_news(topic: str, limit: int):
        raise UpstreamError("NewsAPI exploded", status_code=502, provider="newsapi")

    monkeypatch.setattr("app.routers.gateway.fetch_weather", fake_fetch_weather)
    monkeypatch.setattr("app.routers.gateway.fetch_news", failing_news)

    response = client.get(
        "/api/aggregate",
        params={"city": "Berlin", "topic": "ai"},
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["weather"] is not None
    assert body["news"] is None
    assert "news" in body["errors"]


# --- Upstream error propagation ---------------------------------------------


def test_weather_upstream_error_returns_correct_status(
    client, registered_developer, monkeypatch
):
    _, _, api_key = registered_developer
    from app.upstream.base import UpstreamError

    async def fake_fetch_weather(city: str):
        raise UpstreamError("City not found", status_code=404, provider="openweather")

    monkeypatch.setattr("app.routers.gateway.fetch_weather", fake_fetch_weather)
    response = client.get(
        "/api/weather/Atlantis", headers={"X-API-Key": api_key}
    )
    assert response.status_code == 404
