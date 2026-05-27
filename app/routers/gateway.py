"""Gateway routes for weather, news, finance, and aggregate."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.cache import get_cached, set_cached
from app.config import get_settings
from app.deps import require_api_key
from app.models import APIKey
from app.schemas import (
    AggregateResponse,
    FinanceQuoteResponse,
    NewsResponse,
    WeatherResponse,
)
from app.upstream.base import UpstreamError
from app.upstream.finance import fetch_quote
from app.upstream.news import fetch_news
from app.upstream.weather import fetch_weather

router = APIRouter(prefix="/api", tags=["gateway"])


def _record_upstream_latency(request: Request, latency_ms: int) -> None:
    """Stash upstream latency on `request.state` so the middleware can log it."""
    request.state.upstream_latency_ms = (
        getattr(request.state, "upstream_latency_ms", 0) or 0
    ) + latency_ms


@router.get("/weather/{city}", response_model=WeatherResponse)
async def get_weather(
    city: str,
    request: Request,
    api_key: APIKey = Depends(require_api_key),
) -> WeatherResponse:
    settings = get_settings()
    params = {"city": city.lower()}

    cached = await get_cached("weather", params)
    if cached is not None:
        return WeatherResponse.model_validate(cached)

    try:
        weather, latency_ms = await fetch_weather(city)
    except UpstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    _record_upstream_latency(request, latency_ms)
    await set_cached("weather", params, weather.model_dump(mode="json"), settings.cache_ttl_weather)
    return weather


@router.get("/news", response_model=NewsResponse)
async def get_news(
    request: Request,
    topic: str = Query(..., min_length=1, max_length=128),
    limit: int = Query(10, ge=1, le=100),
    api_key: APIKey = Depends(require_api_key),
) -> NewsResponse:
    settings = get_settings()
    params = {"topic": topic.lower(), "limit": limit}

    cached = await get_cached("news", params)
    if cached is not None:
        return NewsResponse.model_validate(cached)

    try:
        news, latency_ms = await fetch_news(topic, limit)
    except UpstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    _record_upstream_latency(request, latency_ms)
    await set_cached("news", params, news.model_dump(mode="json"), settings.cache_ttl_news)
    return news


@router.get("/finance/quote", response_model=FinanceQuoteResponse)
async def get_finance_quote(
    request: Request,
    symbol: str = Query(..., min_length=1, max_length=16),
    api_key: APIKey = Depends(require_api_key),
) -> FinanceQuoteResponse:
    settings = get_settings()
    params = {"symbol": symbol.upper()}

    cached = await get_cached("finance", params)
    if cached is not None:
        return FinanceQuoteResponse.model_validate(cached)

    try:
        quote, latency_ms = await fetch_quote(symbol)
    except UpstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    _record_upstream_latency(request, latency_ms)
    await set_cached("finance", params, quote.model_dump(mode="json"), settings.cache_ttl_finance)
    return quote


@router.get("/aggregate", response_model=AggregateResponse)
async def get_aggregate(
    request: Request,
    city: str = Query(..., min_length=1, max_length=128),
    topic: str = Query(..., min_length=1, max_length=128),
    limit: int = Query(5, ge=1, le=50),
    api_key: APIKey = Depends(require_api_key),
) -> AggregateResponse:
    """Fan-out: fetch weather + news in parallel and combine."""
    settings = get_settings()
    weather_params = {"city": city.lower()}
    news_params = {"topic": topic.lower(), "limit": limit}

    async def _weather() -> tuple[WeatherResponse | None, int, str | None]:
        cached = await get_cached("weather", weather_params)
        if cached is not None:
            return WeatherResponse.model_validate(cached), 0, None
        try:
            result, latency = await fetch_weather(city)
        except UpstreamError as exc:
            return None, 0, str(exc)
        await set_cached(
            "weather", weather_params, result.model_dump(mode="json"), settings.cache_ttl_weather
        )
        return result, latency, None

    async def _news() -> tuple[NewsResponse | None, int, str | None]:
        cached = await get_cached("news", news_params)
        if cached is not None:
            return NewsResponse.model_validate(cached), 0, None
        try:
            result, latency = await fetch_news(topic, limit)
        except UpstreamError as exc:
            return None, 0, str(exc)
        await set_cached(
            "news", news_params, result.model_dump(mode="json"), settings.cache_ttl_news
        )
        return result, latency, None

    weather_outcome, news_outcome = await asyncio.gather(_weather(), _news())

    total_latency = (weather_outcome[1] or 0) + (news_outcome[1] or 0)
    if total_latency:
        _record_upstream_latency(request, total_latency)

    errors: dict[str, str] = {}
    if weather_outcome[2]:
        errors["weather"] = weather_outcome[2]
    if news_outcome[2]:
        errors["news"] = news_outcome[2]

    return AggregateResponse(
        city=city,
        topic=topic,
        weather=weather_outcome[0],
        news=news_outcome[0],
        errors=errors,
    )
