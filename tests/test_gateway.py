"""Tests for the /api/v1/chat/completions gateway route (mocked NIM upstream)."""

from __future__ import annotations

from app.schemas import ChatCompletionResponse, ChatUsage
from app.upstream.base import UpstreamError


def _chat_fixture(content: str = "Hello from the mock model.") -> ChatCompletionResponse:
    return ChatCompletionResponse(
        model="meta/llama-3.3-70b-instruct",
        content=content,
        usage=ChatUsage(prompt_tokens=12, completion_tokens=20, total_tokens=32),
    )


def _chat_body(prompt: str = "Say hi") -> dict:
    return {"messages": [{"role": "user", "content": prompt}]}


# --- Auth enforcement --------------------------------------------------------


def test_chat_without_api_key_is_401(client):
    response = client.post("/api/v1/chat/completions", json=_chat_body())
    assert response.status_code == 401


def test_chat_with_bad_api_key_is_401(client):
    response = client.post(
        "/api/v1/chat/completions",
        json=_chat_body(),
        headers={"X-API-Key": "af_bogus"},
    )
    assert response.status_code == 401


def test_chat_accepts_authorization_bearer_key(
    client, registered_developer, monkeypatch
):
    """OpenAI-compatible clients send the key as Authorization: Bearer — accept it."""
    _, _, api_key = registered_developer

    async def fake_fetch(req):
        return _chat_fixture(), 10

    monkeypatch.setattr("app.routers.gateway.fetch_chat_completion", fake_fetch)

    response = client.post(
        "/api/v1/chat/completions",
        json=_chat_body(),
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers  # middleware metered it too


# --- Chat route ---------------------------------------------------------------


def test_chat_returns_normalized_completion(client, registered_developer, monkeypatch):
    _, _, api_key = registered_developer

    async def fake_fetch(req):
        return _chat_fixture(), 42

    monkeypatch.setattr("app.routers.gateway.fetch_chat_completion", fake_fetch)

    response = client.post(
        "/api/v1/chat/completions",
        json=_chat_body("Explain rate limiting in one line."),
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 200
    assert response.headers["X-Cache"] == "MISS"
    data = response.json()
    assert data["content"] == "Hello from the mock model."
    assert data["provider"] == "nvidia-nim"
    assert data["usage"]["total_tokens"] == 32


def test_chat_second_identical_request_is_cache_hit(
    client, registered_developer, monkeypatch
):
    """Same prompt twice → second served from Redis, upstream called once."""
    _, _, api_key = registered_developer
    calls = {"n": 0}

    async def fake_fetch(req):
        calls["n"] += 1
        return _chat_fixture(), 42

    monkeypatch.setattr("app.routers.gateway.fetch_chat_completion", fake_fetch)
    headers = {"X-API-Key": api_key}
    body = _chat_body("Deterministic question")

    first = client.post("/api/v1/chat/completions", json=body, headers=headers)
    second = client.post("/api/v1/chat/completions", json=body, headers=headers)

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    assert second.json()["cached"] is True
    assert second.json()["content"] == first.json()["content"]
    assert calls["n"] == 1  # upstream hit only once — the cache saved the second


def test_embeddings_cache_hit_and_savings(client, registered_developer, monkeypatch):
    _, _, api_key = registered_developer
    from app.schemas import ChatUsage, EmbeddingItem, EmbeddingResponse

    calls = {"n": 0}

    async def fake_embed(req):
        calls["n"] += 1
        return (
            EmbeddingResponse(
                model="nvidia/nv-embedqa-e5-v5",
                data=[EmbeddingItem(index=0, embedding=[0.1, 0.2, 0.3])],
                usage=ChatUsage(prompt_tokens=5, total_tokens=5),
            ),
            12,
        )

    monkeypatch.setattr("app.routers.gateway.fetch_embeddings", fake_embed)
    headers = {"X-API-Key": api_key}
    body = {"input": ["the same chunk of text"]}

    miss = client.post("/api/v1/embeddings", json=body, headers=headers)
    hit = client.post("/api/v1/embeddings", json=body, headers=headers)

    assert miss.status_code == 200 and miss.headers["X-Cache"] == "MISS"
    assert hit.headers["X-Cache"] == "HIT"
    assert hit.json()["data"][0]["embedding"] == [0.1, 0.2, 0.3]
    assert calls["n"] == 1


def test_chat_forwards_caller_messages(client, registered_developer, monkeypatch):
    _, _, api_key = registered_developer
    seen = {}

    async def fake_fetch(req):
        seen["messages"] = [m.content for m in req.messages]
        seen["model"] = req.model
        return _chat_fixture(), 5

    monkeypatch.setattr("app.routers.gateway.fetch_chat_completion", fake_fetch)

    client.post(
        "/api/v1/chat/completions",
        json={
            "messages": [{"role": "user", "content": "Write a haiku"}],
            "model": "custom/model",
        },
        headers={"X-API-Key": api_key},
    )
    assert seen["messages"] == ["Write a haiku"]
    assert seen["model"] == "custom/model"


def test_chat_requires_at_least_one_message(client, registered_developer):
    _, _, api_key = registered_developer
    response = client.post(
        "/api/v1/chat/completions",
        json={"messages": []},
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 422


def test_chat_upstream_error_maps_to_http_status(
    client, registered_developer, monkeypatch
):
    _, _, api_key = registered_developer

    async def failing_fetch(req):
        raise UpstreamError("NIM is down", status_code=503, provider="nvidia-nim")

    monkeypatch.setattr("app.routers.gateway.fetch_chat_completion", failing_fetch)

    response = client.post(
        "/api/v1/chat/completions",
        json=_chat_body(),
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 503
    assert "NIM is down" in response.json()["detail"]


def test_chat_missing_nvidia_key_returns_503(client, registered_developer, monkeypatch):
    """Without NVIDIA_API_KEY the upstream client refuses cleanly (no 500)."""
    _, _, api_key = registered_developer
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "nvidia_api_key", "")

    response = client.post(
        "/api/v1/chat/completions",
        json=_chat_body(),
        headers={"X-API-Key": api_key},
    )
    assert response.status_code == 503
    assert "NVIDIA" in response.json()["detail"]
