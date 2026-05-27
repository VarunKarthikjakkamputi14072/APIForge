"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --- Auth ---------------------------------------------------------------------


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RegisterResponse(BaseModel):
    id: int
    email: EmailStr
    tier: str
    api_key: str = Field(description="Plaintext API key. Shown ONCE at registration.")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class DeveloperOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    tier: str
    created_at: datetime


class APIKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime] = None


# --- Gateway / unified responses ---------------------------------------------


class WeatherResponse(BaseModel):
    city: str
    temperature_c: float
    humidity_pct: float
    condition: str
    wind_kph: float
    timestamp: datetime


class NewsArticle(BaseModel):
    title: str
    summary: str
    source: str
    url: str
    published_at: Optional[datetime] = None


class NewsResponse(BaseModel):
    articles: list[NewsArticle]
    total: int
    topic: str


class FinanceQuoteResponse(BaseModel):
    symbol: str
    price: float
    change_pct: float
    volume: int
    market_cap: Optional[float] = None
    timestamp: datetime


class AggregateResponse(BaseModel):
    city: str
    topic: str
    weather: Optional[WeatherResponse] = None
    news: Optional[NewsResponse] = None
    errors: dict[str, str] = Field(default_factory=dict)


# --- Errors -------------------------------------------------------------------


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    retry_after_seconds: Optional[int] = None
