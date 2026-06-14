"""Telemetry tap — a fire-and-forget feed of RAG query signals to Meridian.

Transit sees every query, so it is the natural place to sample them for the
MLOps layer. After each chat completion it emits a small record (query length,
token usage, latency, cache hit) to Meridian's drift monitor, which watches for
the live query distribution drifting away from what the corpus can answer.

The tap is non-blocking and failure-isolated: it is scheduled as a background
task and never propagates an error into the request path, so if Meridian is down
the user's query still succeeds. Disabled by default (MERIDIAN_URL unset) so the
gateway runs standalone — the same drop-in-fakes discipline as the rest of the
platform.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Iterable

from app.config import get_settings
from app.upstream.base import get_http_client

logger = logging.getLogger("transit.telemetry")

# Keep strong references to in-flight tasks so they are not garbage-collected
# before completing (asyncio only holds weak references).
_tasks: set[asyncio.Task] = set()


def last_user_query(messages: Iterable[Any]) -> str:
    """The most recent user message — the thing whose distribution we watch."""
    for message in reversed(list(messages)):
        if getattr(message, "role", None) == "user":
            return getattr(message, "content", "") or ""
    return ""


def build_record(
    *,
    app_id: str,
    model: str,
    query: str,
    usage: dict,
    latency_ms: int,
    cache_hit: bool,
) -> dict:
    """The wire record Meridian appends to its RAG telemetry log."""
    return {
        "ts": time.time(),
        "app": app_id,
        "model": model,
        "query_len": len(query or ""),
        "prompt_tokens": int((usage or {}).get("prompt_tokens", 0)),
        "completion_tokens": int((usage or {}).get("completion_tokens", 0)),
        "total_tokens": int((usage or {}).get("total_tokens", 0)),
        "latency_ms": int(latency_ms or 0),
        "cache_hit": 1 if cache_hit else 0,
    }


async def _post(url: str, record: dict) -> None:
    try:
        client = get_http_client()
        await client.post(url, json=record, timeout=2.0)
    except Exception as exc:  # noqa: BLE001 — the tap must never affect the request
        logger.debug("telemetry post failed: %s", exc)


def tap_chat(
    *,
    api_key: Any,
    body: Any,
    usage: dict,
    latency_ms: int,
    cache_hit: bool,
) -> None:
    """Schedule a telemetry record for one chat completion. No-op if disabled."""
    settings = get_settings()
    url = getattr(settings, "meridian_url", "") or ""
    if not url:
        return
    record = build_record(
        app_id=getattr(api_key, "key_prefix", "unknown"),
        model=getattr(body, "model", None) or settings.nvidia_model,
        query=last_user_query(getattr(body, "messages", []) or []),
        usage=usage or {},
        latency_ms=latency_ms,
        cache_hit=cache_hit,
    )
    try:
        task = asyncio.create_task(_post(url.rstrip("/") + "/telemetry/rag", record))
    except RuntimeError:
        # No running event loop (e.g. called from sync context) — skip silently.
        return
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
