"""Gateway routes — AI chat + embeddings, proxied to NVIDIA NIM with caching.

Transit sits in front of NVIDIA NIM so the apps behind it (MedQuery, ChatDoc)
share one metered, cached key. Identical chat questions and repeated chunk
embeddings are served from Redis — no upstream call, no tokens billed — which is
the whole reason the gateway exists.
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response

from app import cache, telemetry
from app.config import get_settings
from app.deps import require_api_key
from app.models import APIKey
from app.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)
from app.upstream.base import UpstreamError
from app.upstream.llm import fetch_chat_completion, fetch_embeddings

router = APIRouter(prefix="/api", tags=["gateway"])


def _record_upstream_latency(request: Request, latency_ms: int) -> None:
    """Stash upstream latency on `request.state` so the middleware can log it."""
    request.state.upstream_latency_ms = (
        getattr(request.state, "upstream_latency_ms", 0) or 0
    ) + latency_ms


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: Request,
    response: Response,
    body: ChatCompletionRequest = Body(...),
    api_key: APIKey = Depends(require_api_key),
) -> ChatCompletionResponse:
    """OpenAI-compatible chat completion, proxied to NVIDIA NIM with caching.

    The upstream key is injected server-side; the rate-limit middleware meters
    every call. Identical requests (same model + messages + params) return the
    cached completion with `X-Cache: HIT` and bill zero upstream tokens.
    """
    settings = get_settings()
    key = cache.request_hash(
        "chat",
        {
            "model": body.model or settings.nvidia_model,
            "messages": [m.model_dump() for m in body.messages],
            "temperature": body.temperature,
            "max_tokens": body.max_tokens,
        },
    )

    cached = await cache.get_cached(key)
    if cached is not None:
        await cache.record_hit(int(cached.get("usage", {}).get("total_tokens", 0)))
        response.headers["X-Cache"] = "HIT"
        telemetry.tap_chat(
            api_key=api_key, body=body, usage=cached.get("usage", {}),
            latency_ms=0, cache_hit=True,
        )
        return ChatCompletionResponse(**{**cached, "cached": True})

    await cache.record_miss()
    try:
        completion, latency_ms = await fetch_chat_completion(body)
    except UpstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    _record_upstream_latency(request, latency_ms)
    await cache.set_cached(key, completion.model_dump(), settings.cache_ttl_chat)
    response.headers["X-Cache"] = "MISS"
    telemetry.tap_chat(
        api_key=api_key, body=body, usage=completion.usage.model_dump(),
        latency_ms=latency_ms, cache_hit=False,
    )
    return completion


@router.post("/v1/embeddings", response_model=EmbeddingResponse)
async def embeddings(
    request: Request,
    response: Response,
    body: EmbeddingRequest = Body(...),
    api_key: APIKey = Depends(require_api_key),
) -> EmbeddingResponse:
    """Embeddings proxied to NVIDIA NIM, cached by content hash.

    Re-embedding identical text is pure waste — RAG pipelines do it constantly.
    A content-hash cache hit returns the vectors instantly with zero token cost.
    """
    settings = get_settings()
    key = cache.request_hash(
        "embeddings",
        {"model": body.model or settings.nvidia_embedding_model, "input": body.input},
    )

    cached = await cache.get_cached(key)
    if cached is not None:
        await cache.record_hit(int(cached.get("usage", {}).get("total_tokens", 0)))
        response.headers["X-Cache"] = "HIT"
        return EmbeddingResponse(**{**cached, "cached": True})

    await cache.record_miss()
    try:
        result, latency_ms = await fetch_embeddings(body)
    except UpstreamError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    _record_upstream_latency(request, latency_ms)
    await cache.set_cached(key, result.model_dump(), settings.cache_ttl_embeddings)
    response.headers["X-Cache"] = "MISS"
    return result
