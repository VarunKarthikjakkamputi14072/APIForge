"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for Transit.

    Values are read from environment variables (see `.env.example`).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = Field(default="development", alias="APIFORGE_ENV")

    secret_key: str = Field(default="dev-insecure-secret-change-me", alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=60, alias="JWT_EXPIRE_MINUTES")

    database_url: str = Field(
        default="sqlite:///./apiforge.db",
        alias="DATABASE_URL",
    )

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # NVIDIA NIM (build.nvidia.com) — OpenAI-compatible inference backend for the
    # gateway's /api/v1/chat/completions route.
    nvidia_api_key: str = Field(default="", alias="NVIDIA_API_KEY")
    nvidia_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1", alias="NVIDIA_BASE_URL"
    )
    nvidia_model: str = Field(
        default="meta/llama-3.3-70b-instruct", alias="NVIDIA_MODEL"
    )
    nvidia_embedding_model: str = Field(
        default="nvidia/nv-embedqa-e5-v5", alias="NVIDIA_EMBEDDING_MODEL"
    )

    # Chat waterfall: if NVIDIA NIM is down / rate-limited / missing, Transit
    # falls through to these OpenAI-compatible providers in order. All serve
    # Llama 3.3 70B (Gemini is a different model but a strong final fallback).
    # A provider is only in the chain if its key is set.
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_base_url: str = Field(
        default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL"
    )
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")

    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )
    openrouter_model: str = Field(
        default="meta-llama/llama-3.3-70b-instruct", alias="OPENROUTER_MODEL"
    )

    # Google Gemma via NVIDIA NIM (a Google model on NIM infra). Uses a separate
    # NVIDIA key, so it also gives key-level failover: if the primary NIM key is
    # rate-limited, this rung (different key) can still serve.
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    google_base_url: str = Field(
        default="https://integrate.api.nvidia.com/v1", alias="GOOGLE_BASE_URL"
    )
    google_model: str = Field(
        default="google/diffusiongemma-26b-a4b-it", alias="GOOGLE_MODEL"
    )

    # Google Gemini via its OpenAI-compatible endpoint (optional final fallback).
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta/openai",
        alias="GEMINI_BASE_URL",
    )
    gemini_model: str = Field(default="gemini-2.0-flash", alias="GEMINI_MODEL")

    free_tier_requests_per_hour: int = Field(
        default=100, alias="FREE_TIER_REQUESTS_PER_HOUR"
    )
    pro_tier_requests_per_hour: int = Field(
        default=5000, alias="PRO_TIER_REQUESTS_PER_HOUR"
    )

    # Response cache TTLs (seconds). Identical chat/embedding requests within the
    # window are served from Redis — no upstream call, no tokens billed. This is
    # the cost-control core: RAG apps re-ask the same questions and re-embed the
    # same chunks constantly. 0 disables caching for that route.
    cache_ttl_chat: int = Field(default=86400, alias="CACHE_TTL_CHAT")
    cache_ttl_embeddings: int = Field(default=604800, alias="CACHE_TTL_EMBEDDINGS")

    upstream_timeout_seconds: float = Field(default=30.0, alias="UPSTREAM_TIMEOUT_SECONDS")

    # Meridian telemetry tap. When set, Transit fires a non-blocking record of
    # each chat query (length, tokens, latency, cache hit) to Meridian's RAG
    # drift monitor. Empty disables the tap — the gateway runs standalone.
    meridian_url: str = Field(default="", alias="MERIDIAN_URL")

    # Offline fake provider: when no real provider key is set and this is on, the
    # gateway returns a stub completion (usage derived from the prompt) so the
    # whole platform runs with no keys — the same drop-in-fakes discipline as the
    # RAG apps. Off in production, where real keys exist.
    use_fake_provider: bool = Field(default=False, alias="USE_FAKE_PROVIDER")


@lru_cache
def get_settings() -> Settings:
    return Settings()
