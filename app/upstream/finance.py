"""Alpha Vantage client + normalization for stock quotes."""

from __future__ import annotations

from datetime import datetime, timezone

from app.config import get_settings
from app.schemas import FinanceQuoteResponse
from app.upstream.base import UpstreamError, timed_get

ALPHAVANTAGE_URL = "https://www.alphavantage.co/query"


async def fetch_quote(symbol: str) -> tuple[FinanceQuoteResponse, int]:
    settings = get_settings()
    if not settings.alphavantage_api_key:
        raise UpstreamError(
            "Alpha Vantage API key is not configured.",
            status_code=503,
            provider="alphavantage",
        )

    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": settings.alphavantage_api_key,
    }

    async with timed_get(ALPHAVANTAGE_URL, params=params, provider="alphavantage") as timed:
        response = timed.response
        if response.status_code >= 400:
            raise UpstreamError(
                f"Alpha Vantage error {response.status_code}: {response.text[:200]}",
                status_code=502,
                provider="alphavantage",
            )
        data = response.json()
        latency_ms = timed.latency_ms

    quote = data.get("Global Quote") or data.get("globalQuote") or {}
    if not quote or not quote.get("01. symbol"):
        # Common Alpha Vantage rate-limit / empty response
        note = data.get("Note") or data.get("Information") or "no data"
        raise UpstreamError(
            f"Alpha Vantage returned no quote for '{symbol}' ({note}).",
            status_code=404,
            provider="alphavantage",
        )

    return normalize_quote(quote, symbol), latency_ms


def _to_float(value: str | float | int | None, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(str(value).rstrip("%"))
    except (TypeError, ValueError):
        return default


def _to_int(value: str | int | None, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def normalize_quote(quote: dict, symbol: str) -> FinanceQuoteResponse:
    return FinanceQuoteResponse(
        symbol=str(quote.get("01. symbol") or symbol).upper(),
        price=_to_float(quote.get("05. price")),
        change_pct=_to_float(quote.get("10. change percent")),
        volume=_to_int(quote.get("06. volume")),
        # Alpha Vantage GLOBAL_QUOTE doesn't include market cap; left None.
        market_cap=None,
        timestamp=datetime.now(timezone.utc),
    )
