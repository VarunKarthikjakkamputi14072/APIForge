"""The offline fake chat provider — usage and latency scale with prompt size."""

from app.schemas import ChatCompletionRequest
from app.upstream import llm


class _Settings:
    nvidia_model = "meta/llama-3.3-70b-instruct"


def test_fake_completion_shape_and_scaling():
    short = ChatCompletionRequest(messages=[{"role": "user", "content": "hi"}])
    long = ChatCompletionRequest(messages=[{"role": "user", "content": "x" * 800}])

    short_comp, short_latency = llm._fake_completion(short, _Settings())
    long_comp, long_latency = llm._fake_completion(long, _Settings())

    assert short_comp.provider == "fake"
    assert short_comp.usage.total_tokens == (
        short_comp.usage.prompt_tokens + short_comp.usage.completion_tokens
    )
    # bigger prompt -> more tokens and higher latency (the drift signal)
    assert long_comp.usage.prompt_tokens > short_comp.usage.prompt_tokens
    assert long_latency > short_latency
