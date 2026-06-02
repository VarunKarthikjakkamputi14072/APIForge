# APIForge

**Live:** https://apiforge-jnwp.onrender.com

APIForge is a developer-facing API gateway that unifies third-party APIs
(OpenWeather · NewsAPI · Alpha Vantage) behind one rate-limited, authenticated,
analytics-rich REST endpoint — plus a Next.js developer portal to manage keys,
explore requests, and visualize usage.

```
Developer/Client
    ↓
Next.js Developer Portal (key management, explorer, analytics, docs)
    ↓
FastAPI Gateway
    ↓
Redis (rate limiting + response caching)
    ↓
PostgreSQL (API keys, usage logs, analytics)
    ↓
Upstream APIs: OpenWeather | NewsAPI | Alpha Vantage
```

This monorepo contains both stacks:

| Stack | Path | Purpose |
| --- | --- | --- |
| **Gateway** | `app/`, `tests/` | FastAPI + SQLAlchemy + Redis + httpx — the API itself (auth, rate limiting, caching, analytics, normalization). |
| **Developer portal** | [`web/`](./web/README.md) | Next.js 14 + Tailwind dashboard — landing, dashboard, interactive explorer, analytics, docs. |

---

## Gateway (`app/`)

### Features

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

### Stack

FastAPI · SQLAlchemy 2.x · PostgreSQL (SQLite for tests) · Redis · `httpx` (async) · `python-jose` · `bcrypt`

### Project layout

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

### Quickstart

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in upstream API keys + SECRET_KEY

# 2. Run dependencies (Postgres + Redis)
docker compose up -d postgres redis
# Or run everything (gateway included):
docker compose up --build

# 3. Run the API locally
uvicorn app.main:app --reload
# OpenAPI docs at http://localhost:8000/docs
```

```bash
# Register and capture an API key
curl -s -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"supersecret123"}'

# Use the returned api_key
curl -s http://localhost:8000/api/weather/Berlin \
  -H 'X-API-Key: af_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' | jq
```

### Configuration

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

### Database schema

| Table | Columns |
| --- | --- |
| `developers` | `id`, `email` (unique), `hashed_password`, `created_at`, `tier` (`free`/`pro`) |
| `api_keys` | `id`, `developer_id` (FK), `key_hash` (HMAC-SHA256), `key_prefix`, `created_at`, `is_active`, `last_used_at` |
| `request_logs` | `id`, `api_key_id` (FK), `endpoint`, `params` (JSON), `response_time_ms`, `status_code`, `upstream_latency_ms`, `timestamp` |
| `rate_limit_config` | `id`, `tier` (unique), `requests_per_hour` |

Tables are created automatically on startup (`Base.metadata.create_all`). Alembic is included in `requirements.txt` for future migrations.

### Testing

The suite uses a per-test SQLite database and `fakeredis` so it has no external dependencies. Upstream calls are monkey-patched at the router boundary.

```bash
pytest -q
```

24 tests covering auth, normalization, gateway routes, rate-limiter logic, and middleware integration.

### Security notes

- API keys are generated as `af_` + `uuid4().hex`. Only an HMAC-SHA256 hash (peppered with `SECRET_KEY`) is stored, alongside a short prefix for display.
- Passwords are SHA-256 pre-hashed (to bypass bcrypt's 72-byte limit safely) and then bcrypted.
- All upstream calls are async (`httpx.AsyncClient`).
- Rate-limit counters expire automatically at the hour boundary.

---

## Performance

I load-tested the gateway with [k6](https://k6.io) against three scenarios: auth ramp (0→200 concurrent users), cache stampede (50 VUs hitting the same cold key simultaneously), and sustained mixed traffic. The test script is at [`docs/benchmarks/load_test.js`](./docs/benchmarks/load_test.js).

### Results (200 peak VUs, 4 uvicorn workers)

| Metric | Result |
|---|---|
| Throughput | **276 req/s** sustained |
| Median response time | **45ms** |
| p95 response time | 325ms |
| Cache hit rate | **54.6%** (warm caches higher) |
| Total requests handled | 63,559 |

### What the test found and how it was fixed

**Problem 1 — Synchronous DB writes blocking the event loop**

The request logger (`_persist_log`) was opening a sync SQLAlchemy session and committing on the event loop for every `/api/*` request. Under 200 concurrent users this stacked 200 blocking DB commits — the event loop froze and every request timed out at 60s.

Fix: all sync DB work now runs in `asyncio.to_thread()`. Logging is fire-and-forget via `loop.create_task(asyncio.to_thread(...))` — the response is returned to the client before the log write starts.

**Problem 2 — Per-request DB lookup on the auth path**

Every request hit Postgres to resolve API key → developer tier, even for the same key called repeatedly. Under load this exhausted the connection pool.

Fix: a Redis key→tier cache (`keytier:<hash>`, 60s TTL) means the DB is only hit once per key per minute. Subsequent requests resolve tier from Redis in under 1ms.

**Problem 3 — Cache stampede on cold keys**

When 50 concurrent requests all missed the same cache key, 50 upstream calls went out simultaneously.

Fix: single-flight lock via Redis `SET NX` — only one caller fetches the upstream value, the rest wait and read the populated cache. `upstream_calls_total` in the k6 summary drops from 50 to 1 on a cold key.

To run the load test yourself:

```bash
brew install k6
docker compose up -d
k6 run docs/benchmarks/load_test.js \
  -e API_KEY=af_your_key \
  -e BASE_URL=http://localhost:8000
```

---

## Developer portal (`web/`)

A dark, terminal-themed developer console built with **Next.js 14** (App Router,
TypeScript) and **Tailwind CSS**.

| Route | Description |
| --- | --- |
| `/` | Landing page with feature highlights and pricing (Free 100 req/hr · Pro 1,000 req/hr) |
| `/dashboard` | Masked API key (reveal/copy/rotate/revoke), usage stats, hourly chart, quick-start snippets |
| `/explorer` | Interactive request builder — normalized response next to raw upstream payload |
| `/analytics` | Hourly volume area chart, requests-by-endpoint bar chart, recent requests table |
| `/docs` | OpenAPI-style reference with curl / Python / JavaScript tabs for every endpoint |

Reusable components: `ApiKeyCard`, `RequestLog`, `UsageChart` (recharts),
`CodeSnippet` (custom token-based highlighter).

```bash
cd web
npm install
cp .env.example .env.local         # optional: NEXT_PUBLIC_APIFORGE_BASE_URL
npm run dev                         # http://localhost:3000
npm run build && npm run start      # production
```

See [`web/README.md`](./web/README.md) for full details. The portal runs in
**demo mode** with mocked data if the gateway URL is not configured, so it's
fully browsable offline.

---

## License

MIT
