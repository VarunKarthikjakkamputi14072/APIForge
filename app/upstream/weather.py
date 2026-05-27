"""OpenWeather client + normalization to APIForge's unified schema."""

from __future__ import annotations

from datetime import datetime, timezone

from app.config import get_settings
from app.schemas import WeatherResponse
from app.upstream.base import UpstreamError, timed_get

OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


async def fetch_weather(city: str) -> tuple[WeatherResponse, int]:
    """Return ``(normalized_weather, upstream_latency_ms)`` for ``city``."""
    settings = get_settings()
    if not settings.openweather_api_key:
        raise UpstreamError(
            "OpenWeather API key is not configured.",
            status_code=503,
            provider="openweather",
        )

    params = {
        "q": city,
        "appid": settings.openweather_api_key,
        "units": "metric",
    }

    async with timed_get(OPENWEATHER_URL, params=params, provider="openweather") as timed:
        response = timed.response
        if response.status_code == 404:
            raise UpstreamError(
                f"City '{city}' not found.", status_code=404, provider="openweather"
            )
        if response.status_code >= 400:
            raise UpstreamError(
                f"OpenWeather error {response.status_code}: {response.text[:200]}",
                status_code=502,
                provider="openweather",
            )

        data = response.json()
        latency_ms = timed.latency_ms

    return normalize_weather(data), latency_ms


def normalize_weather(data: dict) -> WeatherResponse:
    main = data.get("main") or {}
    wind = data.get("wind") or {}
    weather_arr = data.get("weather") or []
    condition = (weather_arr[0].get("main") if weather_arr else None) or "Unknown"

    wind_ms = float(wind.get("speed", 0.0))
    wind_kph = round(wind_ms * 3.6, 2)

    ts = data.get("dt")
    timestamp = (
        datetime.fromtimestamp(ts, tz=timezone.utc) if ts else datetime.now(timezone.utc)
    )

    return WeatherResponse(
        city=str(data.get("name") or "").strip() or "unknown",
        temperature_c=float(main.get("temp", 0.0)),
        humidity_pct=float(main.get("humidity", 0.0)),
        condition=str(condition),
        wind_kph=wind_kph,
        timestamp=timestamp,
    )
