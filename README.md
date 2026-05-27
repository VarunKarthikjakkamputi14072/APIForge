# APIForge

APIForge is a developer-facing API gateway built with **FastAPI**. It connects to multiple
third-party APIs (OpenWeather, NewsAPI, Alpha Vantage), normalizes their responses into a
unified schema, and exposes a single REST surface with **API-key authentication**, **Redis
rate limiting**, **response caching**, and **usage analytics** persisted in PostgreSQL.

```
Developer/Client
    ↓
FastAPI Gateway  ──►  Redis (rate limiting + response caching)
    ↓                     ↑
PostgreSQL (API keys, usage logs, analytics)
    ↓
Upstream APIs: OpenWeather | NewsAPI | Alpha Vantage
```

## Features

- **Authentication**
  - `POST /auth/register` — creates a developer account and returns a freshly minted API key prefixed with `af_` (stored hashed via HMAC-SHA256, password hashed with bcrypt).
  - `POST /auth/login` — returns a JWT (`python-jose`, HS256).
  - `GET /auth/me`, `GET /auth/keys` — inspect the current developer / their keys (requires `X-API-Key`).
- **Gateway routes** (require `X-API-Key`)
  - `GET /api/weather/{city}` — OpenWeather, normalized to `{city, temperature_c, humidity_pct, condition, wind_kph, timestamp}`.
  - `GET /api/news?topic={topic}&limit={n}` — NewsAPI, normalized to `{articles: [{title, summary, source, url, published_at}], total, topic}`.
  - `GET /api/finance/quote?symbol={ticker}` — Alpha Vantage, normalized to `{symbol, price, change_pct, volume, market_cap, timestamp}`.
  - `GET /api/aggregate?city={city}&topic={topic}` — fan-out: calls weather + news in parallel using `asyncio.gather` and returns a combined response (partial failures are reported in `errors`).
- **Rate limiting** (Redis)
  - Configurable per-tier limits, defaults to **100 req/hour** for the `free` tier.
  - Redis key pattern: `ratelimit:{api_key}:{hour_bucket}`.
  - Returns `429` with `retry_after_seconds` when exceeded, plus `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` headers on every `/api/*` response.
- **Caching** (Redis)
  - Weather: **10 min**, News: **5 min**, Finance: **1 min** (overridable via env vars).
  - Cache key pattern: `cache:{route}:{params_hash}` (SHA-256 of normalized JSON params).
- **Usage analytics**
  - Every `/api/*` request is logged to `request_logs` (endpoint, params, response_time_ms, status_code, upstream_latency_ms) via Starlette middleware.

## Stack

FastAPI · SQLAlchemy 2.x · PostgreSQL (SQLite for tests) · Redis · `httpx` (async) · `python-jose` · `bcrypt`

## Project layout

```
app/
  main.py            # FastAPI app factory + lifespan
  config.py          # pydantic-settings configuration
  database.py        # SQLAlchemy engine/session/Base
  models.py          # Developer, APIKey, RequestLog, RateLimitConfig
  schemas.py         # Pydantic request/response schemas
  security.py        # password hashing, API key gen, JWT
  deps.py            # FastAPI dependencies (API-key resolution)
  redis_client.py    # async Redis client (override-able for tests)
  rate_limit.py      # Redis-backed hourly limiter
  cache.py           # Redis-backed response cache
  middleware.py      # /api/* rate-limit + request logging middleware
  routers/
    auth.py          # /auth/*
    gateway.py       # /api/*
  upstream/
    base.py          # shared async httpx client
    weather.py       # OpenWeather + normalization
    news.py          # NewsAPI + normalization
    finance.py       # Alpha Vantage + normalization
tests/               # pytest test suite (uses SQLite + fakeredis)
docker-compose.yml   # Postgres + Redis + app
Dockerfile
requirements.txt
.env.example
```

## Quickstart

### 1. Install

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in upstream API keys + SECRET_KEY
```

### 2. Run dependencies (Postgres + Redis)

```bash
docker compose up -d postgres redis
```

Or run everything (gateway included) with:

```bash
docker compose up --build
```

### 3. Run the API locally

```bash
uvicorn app.main:app --reload
# OpenAPI docs at http://localhost:8000/docs
```

### 4. Try it

```bash
# Register and capture an API key
curl -s -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"supersecret123"}'

# Use the returned api_key
curl -s http://localhost:8000/api/weather/Berlin \
  -H 'X-API-Key: af_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' | jq
```

## Configuration

All settings are loaded from environment variables (see `.env.example`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./apiforge.db` | SQLAlchemy URL (use `postgresql+psycopg2://...` in production) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `SECRET_KEY` | dev-only placeholder | Used for JWT signing and API-key HMAC pepper |
| `JWT_ALGORITHM` / `JWT_EXPIRE_MINUTES` | `HS256` / `60` | JWT issuance |
| `OPENWEATHER_API_KEY` / `NEWSAPI_API_KEY` / `ALPHAVANTAGE_API_KEY` | empty | Upstream credentials |
| `FREE_TIER_REQUESTS_PER_HOUR` / `PRO_TIER_REQUESTS_PER_HOUR` | `100` / `5000` | Seeded into `rate_limit_config` on startup |
| `CACHE_TTL_WEATHER` / `CACHE_TTL_NEWS` / `CACHE_TTL_FINANCE` | `600` / `300` / `60` | Cache TTLs in seconds |
| `UPSTREAM_TIMEOUT_SECONDS` | `10` | `httpx` per-request timeout |

## Database schema

| Table | Columns |
| --- | --- |
| `developers` | `id`, `email` (unique), `hashed_password`, `created_at`, `tier` (`free`/`pro`) |
| `api_keys` | `id`, `developer_id` (FK), `key_hash` (HMAC-SHA256), `key_prefix`, `created_at`, `is_active`, `last_used_at` |
| `request_logs` | `id`, `api_key_id` (FK), `endpoint`, `params` (JSON), `response_time_ms`, `status_code`, `upstream_latency_ms`, `timestamp` |
| `rate_limit_config` | `id`, `tier` (unique), `requests_per_hour` |

Tables are created automatically on startup (`Base.metadata.create_all`). Alembic is included in `requirements.txt` for future migrations.

## Testing

The suite uses a per-test SQLite database and `fakeredis` so it has no external dependencies. Upstream calls are monkey-patched at the router boundary.

```bash
pytest -q
```

Currently **24 tests** covering auth, normalization, gateway routes, rate-limiter logic, and middleware integration.

## Security notes

- API keys are generated as `af_` + `uuid4().hex`. Only an HMAC-SHA256 hash (peppered with `SECRET_KEY`) is stored, alongside a short prefix for display.
- Passwords are SHA-256 pre-hashed (to bypass bcrypt's 72-byte limit safely) and then bcrypted.
- All upstream calls are async (`httpx.AsyncClient`).
- Rate-limit counters expire automatically at the hour boundary.

## License

MIT
