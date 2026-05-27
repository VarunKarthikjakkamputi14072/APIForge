"""Unit tests for upstream response normalization."""

from __future__ import annotations

from app.upstream.finance import normalize_quote
from app.upstream.news import normalize_news
from app.upstream.weather import normalize_weather


def test_normalize_weather_shapes_unified_schema():
    raw = {
        "name": "Berlin",
        "dt": 1_700_000_000,
        "main": {"temp": 12.3, "humidity": 73},
        "wind": {"speed": 4.2},  # m/s
        "weather": [{"main": "Clouds", "description": "broken clouds"}],
    }
    result = normalize_weather(raw)
    assert result.city == "Berlin"
    assert result.temperature_c == 12.3
    assert result.humidity_pct == 73
    assert result.condition == "Clouds"
    assert result.wind_kph == round(4.2 * 3.6, 2)


def test_normalize_weather_tolerates_missing_fields():
    result = normalize_weather({})
    assert result.city == "unknown"
    assert result.temperature_c == 0.0
    assert result.condition == "Unknown"


def test_normalize_news_maps_articles():
    raw = {
        "totalResults": 2,
        "articles": [
            {
                "title": "Headline A",
                "description": "Summary A",
                "url": "https://x.test/a",
                "publishedAt": "2024-04-12T08:30:00Z",
                "source": {"name": "TestWire"},
            },
            {
                "title": "Headline B",
                "description": None,
                "content": "Body B",
                "url": "https://x.test/b",
                "publishedAt": "invalid-date",
                "source": {"name": None},
            },
        ],
    }
    result = normalize_news(raw, topic="ai")
    assert result.total == 2
    assert result.topic == "ai"
    assert result.articles[0].source == "TestWire"
    assert result.articles[0].published_at is not None
    assert result.articles[1].summary == "Body B"
    assert result.articles[1].source == "unknown"
    assert result.articles[1].published_at is None


def test_normalize_quote_parses_strings():
    raw = {
        "01. symbol": "AAPL",
        "05. price": "189.4200",
        "06. volume": "12345678",
        "10. change percent": "1.2300%",
    }
    result = normalize_quote(raw, symbol="aapl")
    assert result.symbol == "AAPL"
    assert result.price == 189.42
    assert result.change_pct == 1.23
    assert result.volume == 12_345_678
    assert result.market_cap is None
