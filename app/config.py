"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for APIForge.

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

    openweather_api_key: str = Field(default="", alias="OPENWEATHER_API_KEY")
    newsapi_api_key: str = Field(default="", alias="NEWSAPI_API_KEY")
    alphavantage_api_key: str = Field(default="", alias="ALPHAVANTAGE_API_KEY")

    free_tier_requests_per_hour: int = Field(
        default=100, alias="FREE_TIER_REQUESTS_PER_HOUR"
    )
    pro_tier_requests_per_hour: int = Field(
        default=5000, alias="PRO_TIER_REQUESTS_PER_HOUR"
    )

    cache_ttl_weather: int = Field(default=600, alias="CACHE_TTL_WEATHER")
    cache_ttl_news: int = Field(default=300, alias="CACHE_TTL_NEWS")
    cache_ttl_finance: int = Field(default=60, alias="CACHE_TTL_FINANCE")

    upstream_timeout_seconds: float = Field(default=10.0, alias="UPSTREAM_TIMEOUT_SECONDS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
