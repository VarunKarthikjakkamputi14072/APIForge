# APIForge — Developer Portal

A Next.js 14 + Tailwind CSS dashboard for the [APIForge](../README.md) gateway.

## Pages

| Route | Purpose |
| --- | --- |
| `/` | Landing — product pitch, pricing tiers (Free 100 req/hr · Pro 1,000 req/hr), CTAs |
| `/dashboard` | API key card (masked, reveal, copy, rotate, revoke), usage stats, hourly chart, quick-start snippets |
| `/explorer` | Interactive request builder; side-by-side **normalized** and **raw upstream** response panels |
| `/analytics` | Area chart (hourly volume), bar chart (requests by endpoint), recent requests table |
| `/docs` | OpenAPI-style reference for every endpoint with curl / Python / JavaScript tabs |

## Components

- **`ApiKeyCard`** — masked key, reveal/copy/rotate/revoke, created-at timestamp, tier.
- **`RequestLog`** (`RequestLogTable` / `RequestLogRow`) — latency badge (green <200ms, amber <500ms, red ≥500ms) and status badge.
- **`UsageChart`** — recharts area chart of hourly request volume with the terminal-green theme.
- **`CodeSnippet`** — language-tabbed snippet block (Python / JavaScript / curl / JSON) with built-in syntax highlighting and one-click copy.

## Design

Dark "developer tool" aesthetic — slate background with a subtle grid, emerald terminal-green accents (`#22d3a3`), and a monospaced display font for keys, paths, and code. The shared `panel` / `btn-primary` / `btn-ghost` / `badge` Tailwind components in `app/globals.css` are the source of truth.

## Quickstart

```bash
cd web
npm install
cp .env.example .env.local   # optional — set NEXT_PUBLIC_APIFORGE_BASE_URL
npm run dev                  # http://localhost:3000
```

If `NEXT_PUBLIC_APIFORGE_BASE_URL` is unset the portal runs in **demo mode** with mocked data so you can browse and screenshot it offline. When set, the Explorer and Dashboard hit the real FastAPI gateway and inject the API key stored in `localStorage`.

## Scripts

- `npm run dev` — Next.js dev server with HMR
- `npm run build` — production build (all pages prerender as static)
- `npm run start` — serve the production build
- `npm run lint` — ESLint
- `npm run type-check` — strict `tsc --noEmit`

## Tech

Next.js 14 (App Router, TypeScript, strict mode) · Tailwind CSS 3.4 · Recharts 2.x · lucide-react · custom lightweight syntax highlighter (no Prism/Shiki dependency).
