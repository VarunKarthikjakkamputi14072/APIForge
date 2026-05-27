"""APIForge FastAPI entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import __version__
from app.config import get_settings
from app.database import SessionLocal, get_db, init_db
from app.middleware import APIKeyRateLimitAndLogMiddleware
from app.models import RateLimitConfig
from app.redis_client import close_redis
from app.routers import auth, gateway
from app.upstream.base import close_http_client


def _seed_rate_limit_config(db: Session) -> None:
    settings = get_settings()
    seeds = {
        "free": settings.free_tier_requests_per_hour,
        "pro": settings.pro_tier_requests_per_hour,
    }
    existing = {
        row.tier
        for row in db.execute(select(RateLimitConfig)).scalars().all()
    }
    for tier, requests_per_hour in seeds.items():
        if tier not in existing:
            db.add(RateLimitConfig(tier=tier, requests_per_hour=requests_per_hour))
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        _seed_rate_limit_config(db)
    finally:
        db.close()
    try:
        yield
    finally:
        await close_redis()
        await close_http_client()


def create_app() -> FastAPI:
    app = FastAPI(
        title="APIForge",
        version=__version__,
        description=(
            "APIForge is a developer API gateway that fans out to upstream services "
            "(OpenWeather, NewsAPI, Alpha Vantage) and exposes a unified, rate-limited, "
            "authenticated REST surface."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(APIKeyRateLimitAndLogMiddleware)

    app.include_router(auth.router)
    app.include_router(gateway.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.get("/", tags=["meta"])
    def root() -> dict[str, str]:
        return {
            "name": "APIForge",
            "version": __version__,
            "docs": "/docs",
        }

    @app.get("/admin/rate-limits", tags=["meta"])
    def list_rate_limits(db: Session = Depends(get_db)) -> list[dict]:
        rows = db.execute(select(RateLimitConfig)).scalars().all()
        return [{"tier": r.tier, "requests_per_hour": r.requests_per_hour} for r in rows]

    return app


app = create_app()
