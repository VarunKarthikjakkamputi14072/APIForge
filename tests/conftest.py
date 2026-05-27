"""Shared test fixtures.

The test environment uses:
* a per-test SQLite database (file-backed so background threads from
  Starlette's middleware can share it),
* a `fakeredis` instance in place of the real Redis,
* monkey-patched upstream HTTP clients.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

# Default to safe in-process settings BEFORE app modules import.
os.environ.setdefault("APIFORGE_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-please-change")
os.environ.setdefault("OPENWEATHER_API_KEY", "test-openweather")
os.environ.setdefault("NEWSAPI_API_KEY", "test-newsapi")
os.environ.setdefault("ALPHAVANTAGE_API_KEY", "test-alphavantage")
os.environ.setdefault("FREE_TIER_REQUESTS_PER_HOUR", "5")

# Ensure repo root is importable.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import fakeredis.aioredis as fakeredis_async

from app import database, redis_client
from app.config import get_settings


@pytest.fixture
def settings_override(tmp_path, monkeypatch):
    db_path = tmp_path / "apiforge_test.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def test_engine(settings_override):
    engine = create_engine(
        settings_override.database_url,
        future=True,
        connect_args={"check_same_thread": False},
    )
    return engine


@pytest.fixture
def test_db(test_engine, monkeypatch):
    """Bind the app's SessionLocal/engine to the per-test database."""
    TestingSessionLocal = sessionmaker(
        bind=test_engine, autoflush=False, autocommit=False, future=True
    )
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setattr(database, "SessionLocal", TestingSessionLocal)
    # Some modules captured `SessionLocal` at import time — patch those too.
    from app import middleware as _mw

    monkeypatch.setattr(_mw, "SessionLocal", TestingSessionLocal)

    database.init_db()
    return TestingSessionLocal


@pytest.fixture
def fake_redis():
    client = fakeredis_async.FakeRedis(decode_responses=True)
    redis_client.set_redis_client(client)
    yield client
    redis_client.set_redis_client(None)  # type: ignore[arg-type]


@pytest.fixture
def app(test_db, fake_redis, monkeypatch):
    # Build app *after* fixtures have patched DB + Redis.
    from app.main import create_app

    application = create_app()
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture
def registered_developer(client):
    """Register a fresh developer and return `(email, password, api_key)`."""
    email = f"dev-{uuid.uuid4().hex[:8]}@example.com"
    password = "supersecret123"
    response = client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return email, password, body["api_key"]
