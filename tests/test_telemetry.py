"""Tests for the Meridian telemetry tap (no network — pure record building)."""

from __future__ import annotations

from app import telemetry
from app.schemas import ChatCompletionRequest


def test_last_user_query_picks_the_most_recent_user_message():
    body = ChatCompletionRequest(
        messages=[
            {"role": "system", "content": "you are helpful"},
            {"role": "user", "content": "first question"},
            {"role": "assistant", "content": "an answer"},
            {"role": "user", "content": "the latest question"},
        ]
    )
    assert telemetry.last_user_query(body.messages) == "the latest question"


def test_build_record_shape_and_types():
    record = telemetry.build_record(
        app_id="af_a1b2",
        model="meta/llama-3.3-70b-instruct",
        query="what is the HbA1c trend?",
        usage={"prompt_tokens": 12, "completion_tokens": 20, "total_tokens": 32},
        latency_ms=145,
        cache_hit=False,
    )
    assert record["app"] == "af_a1b2"
    assert record["query_len"] == len("what is the HbA1c trend?")
    assert record["total_tokens"] == 32
    assert record["latency_ms"] == 145
    assert record["cache_hit"] == 0
    assert isinstance(record["ts"], float)


def test_tap_chat_is_noop_when_meridian_url_unset(monkeypatch):
    # Default settings have MERIDIAN_URL empty -> the tap must not schedule work
    # or raise, even outside an event loop.
    before = len(telemetry._tasks)
    telemetry.tap_chat(
        api_key=object(),
        body=ChatCompletionRequest(messages=[{"role": "user", "content": "hi"}]),
        usage={"total_tokens": 5},
        latency_ms=10,
        cache_hit=False,
    )
    assert len(telemetry._tasks) == before
