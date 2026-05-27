"""NewsAPI client + normalization."""

from __future__ import annotations

from datetime import datetime

from app.config import get_settings
from app.schemas import NewsArticle, NewsResponse
from app.upstream.base import UpstreamError, timed_get

NEWSAPI_URL = "https://newsapi.org/v2/everything"


async def fetch_news(topic: str, limit: int) -> tuple[NewsResponse, int]:
    settings = get_settings()
    if not settings.newsapi_api_key:
        raise UpstreamError(
            "NewsAPI key is not configured.", status_code=503, provider="newsapi"
        )

    limit = max(1, min(limit, 100))
    params = {
        "q": topic,
        "pageSize": limit,
        "language": "en",
        "sortBy": "publishedAt",
        "apiKey": settings.newsapi_api_key,
    }

    async with timed_get(NEWSAPI_URL, params=params, provider="newsapi") as timed:
        response = timed.response
        if response.status_code >= 400:
            raise UpstreamError(
                f"NewsAPI error {response.status_code}: {response.text[:200]}",
                status_code=502,
                provider="newsapi",
            )
        data = response.json()
        latency_ms = timed.latency_ms

    return normalize_news(data, topic), latency_ms


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        # NewsAPI uses e.g. "2024-04-12T08:30:00Z"
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize_news(data: dict, topic: str) -> NewsResponse:
    raw_articles = data.get("articles") or []
    articles: list[NewsArticle] = []
    for item in raw_articles:
        source = (item.get("source") or {}).get("name") or "unknown"
        articles.append(
            NewsArticle(
                title=str(item.get("title") or "").strip() or "(untitled)",
                summary=str(item.get("description") or item.get("content") or "").strip(),
                source=str(source),
                url=str(item.get("url") or ""),
                published_at=_parse_iso(item.get("publishedAt")),
            )
        )

    total = int(data.get("totalResults") or len(articles))
    return NewsResponse(articles=articles, total=total, topic=topic)
