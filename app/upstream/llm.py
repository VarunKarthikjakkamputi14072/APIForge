"""Chat + embedding clients for the upstream LLM providers.

Chat uses a provider **waterfall**: NVIDIA NIM primary, then Groq → OpenRouter →
Gemini as fallbacks. If a provider is down, rate-limited, or unconfigured, the
gateway falls through to the next, so a single provider outage doesn't take chat
down. All are OpenAI-compatible; their keys live server-side only and are
injected as `Authorization: Bearer`. Embeddings use NVIDIA NIM.
"""

from __future__ import annotations

import time

from app.config import get_settings
from app.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatUsage,
    EmbeddingItem,
    EmbeddingRequest,
    EmbeddingResponse,
)
from app.upstream.base import UpstreamError, get_http_client


def _chat_providers(settings) -> list[tuple[str, str, str, str]]:
    """Ordered chat waterfall: (name, base_url, api_key, default_model).

    NVIDIA NIM is primary; Groq, OpenRouter, then Gemini are fallbacks. Only
    providers with a configured key are included. Centralizing the keys here is
    the point of the gateway — the apps behind it never see any of them.
    """
    s = settings
    candidates = [
        ("nvidia-nim", s.nvidia_base_url, s.nvidia_api_key, s.nvidia_model),
        ("groq", s.groq_base_url, s.groq_api_key, s.groq_model),
        ("openrouter", s.openrouter_base_url, s.openrouter_api_key, s.openrouter_model),
        ("google-gemma", s.google_base_url, s.google_api_key, s.google_model),
        ("gemini", s.gemini_base_url, s.gemini_api_key, s.gemini_model),
    ]
    return [(n, b, k, m) for (n, b, k, m) in candidates if k]


async def fetch_chat_completion(
    req: ChatCompletionRequest,
) -> tuple[ChatCompletionResponse, int]:
    """Return ``(completion, upstream_latency_ms)`` via the provider waterfall.

    Tries each configured provider in order; on a network error or HTTP >=400
    (rate limit, outage, bad model), it falls through to the next. Returns the
    first success, tagged with the provider that served it. Raises only if every
    provider fails.
    """
    settings = get_settings()
    providers = _chat_providers(settings)
    if not providers:
        if settings.use_fake_provider:
            return _fake_completion(req, settings)
        raise UpstreamError(
            "No chat provider configured (set NVIDIA_API_KEY or a fallback key).",
            status_code=503,
            provider="none",
        )

    client = get_http_client()
    errors: list[str] = []
    for i, (name, base_url, api_key, default_model) in enumerate(providers):
        # Honor an explicit model override only on the primary; fallbacks use
        # their own model (the override likely isn't valid on another provider).
        model = (req.model or default_model) if i == 0 else default_model
        payload = {
            "model": model,
            "messages": [m.model_dump() for m in req.messages],
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        url = f"{base_url.rstrip('/')}/chat/completions"
        start = time.perf_counter()
        try:
            response = await client.post(url, json=payload, headers=headers)
        except Exception as exc:  # network / timeout → try next provider
            errors.append(f"{name}: {exc}")
            continue
        latency_ms = int((time.perf_counter() - start) * 1000)

        if response.status_code >= 400:
            errors.append(f"{name}: HTTP {response.status_code} {response.text[:120]}")
            continue

        return _normalize(response.json(), model, provider=name), latency_ms

    raise UpstreamError(
        "All chat providers failed — " + " | ".join(errors),
        status_code=502,
        provider="waterfall",
    )


def _fake_completion(
    req: ChatCompletionRequest, settings
) -> tuple[ChatCompletionResponse, int]:
    """Offline stub completion. Usage and latency scale with the prompt size so
    bigger / off-corpus queries produce larger token counts and slower answers —
    a realistic signal for the downstream drift monitor."""
    text = " ".join((m.content or "") for m in req.messages)
    prompt_tokens = max(1, len(text) // 4)
    completion_tokens = 40 + prompt_tokens // 10
    latency_ms = 200 + prompt_tokens // 2
    usage = ChatUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
    )
    completion = ChatCompletionResponse(
        model=req.model or settings.nvidia_model or "fake-model",
        content="[offline] Stubbed answer from Transit's fake provider (no upstream key).",
        usage=usage,
        provider="fake",
    )
    return completion, latency_ms


def _normalize(data: dict, model: str, provider: str = "nvidia-nim") -> ChatCompletionResponse:
    choices = data.get("choices") or []
    content = ""
    if choices:
        message = choices[0].get("message") or {}
        content = message.get("content") or ""

    usage_raw = data.get("usage") or {}
    usage = ChatUsage(
        prompt_tokens=int(usage_raw.get("prompt_tokens", 0) or 0),
        completion_tokens=int(usage_raw.get("completion_tokens", 0) or 0),
        total_tokens=int(usage_raw.get("total_tokens", 0) or 0),
    )

    return ChatCompletionResponse(
        model=str(data.get("model") or model),
        content=content,
        usage=usage,
        provider=provider,
    )


async def fetch_embeddings(
    req: EmbeddingRequest,
) -> tuple[EmbeddingResponse, int]:
    """Return ``(embeddings, upstream_latency_ms)`` from NVIDIA NIM.

    Used by RAG apps (MedQuery, ChatDoc) to embed document chunks and queries.
    The gateway caches these aggressively — re-embedding identical text is pure
    waste, so a content-hash cache hit returns instantly with zero token cost.
    """
    settings = get_settings()
    if not settings.nvidia_api_key:
        raise UpstreamError(
            "NVIDIA NIM API key is not configured (set NVIDIA_API_KEY).",
            status_code=503,
            provider="nvidia-nim",
        )

    model = req.model or settings.nvidia_embedding_model
    payload = {
        "model": model,
        "input": req.input,
        # NVIDIA embedding models require an input_type; "passage" suits both
        # indexing and query embedding for retrieval-style models.
        "input_type": "passage",
    }
    headers = {
        "Authorization": f"Bearer {settings.nvidia_api_key}",
        "Content-Type": "application/json",
    }

    client = get_http_client()
    url = f"{settings.nvidia_base_url.rstrip('/')}/embeddings"
    start = time.perf_counter()
    try:
        response = await client.post(url, json=payload, headers=headers)
    except Exception as exc:  # network / timeout
        raise UpstreamError(
            f"NVIDIA NIM embeddings request failed: {exc}",
            status_code=504,
            provider="nvidia-nim",
        ) from exc
    latency_ms = int((time.perf_counter() - start) * 1000)

    if response.status_code >= 400:
        raise UpstreamError(
            f"NVIDIA NIM embeddings error {response.status_code}: {response.text[:300]}",
            status_code=502,
            provider="nvidia-nim",
        )

    data = response.json()
    items = [
        EmbeddingItem(
            index=int(d.get("index", i)),
            embedding=[float(x) for x in (d.get("embedding") or [])],
        )
        for i, d in enumerate(data.get("data") or [])
    ]
    usage_raw = data.get("usage") or {}
    usage = ChatUsage(
        prompt_tokens=int(usage_raw.get("prompt_tokens", 0) or 0),
        total_tokens=int(usage_raw.get("total_tokens", 0) or 0),
    )
    return (
        EmbeddingResponse(
            model=str(data.get("model") or model),
            data=items,
            usage=usage,
        ),
        latency_ms,
    )
