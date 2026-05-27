import type { EndpointId } from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_APIFORGE_BASE_URL?.replace(/\/$/, "") ?? "";

export const HAS_LIVE_BACKEND = API_BASE_URL.length > 0;

export type ApiResult<T> = {
  ok: boolean;
  status: number;
  latencyMs: number;
  data: T | null;
  raw: unknown;
  error?: string;
};

const ENDPOINT_PATHS: Record<EndpointId, (params: Record<string, string>) => string> = {
  weather: (p) => `/api/weather/${encodeURIComponent(p.city || "Berlin")}`,
  news: (p) => {
    const q = new URLSearchParams({ topic: p.topic || "ai", limit: p.limit || "5" });
    return `/api/news?${q.toString()}`;
  },
  finance: (p) => {
    const q = new URLSearchParams({ symbol: p.symbol || "AAPL" });
    return `/api/finance/quote?${q.toString()}`;
  },
  aggregate: (p) => {
    const q = new URLSearchParams({
      city: p.city || "Berlin",
      topic: p.topic || "ai",
    });
    return `/api/aggregate?${q.toString()}`;
  },
};

export function buildPath(endpoint: EndpointId, params: Record<string, string>): string {
  return ENDPOINT_PATHS[endpoint](params);
}

export async function callEndpoint<T = unknown>(
  endpoint: EndpointId,
  params: Record<string, string>,
  apiKey: string,
): Promise<ApiResult<T>> {
  const path = buildPath(endpoint, params);
  if (!HAS_LIVE_BACKEND) {
    return {
      ok: false,
      status: 0,
      latencyMs: 0,
      data: null,
      raw: null,
      error:
        "Live backend not configured. Set NEXT_PUBLIC_APIFORGE_BASE_URL to call the gateway.",
    };
  }

  const url = `${API_BASE_URL}${path}`;
  const started = performance.now();
  try {
    const response = await fetch(url, {
      headers: apiKey ? { "X-API-Key": apiKey } : undefined,
      cache: "no-store",
    });
    const latencyMs = Math.round(performance.now() - started);
    const text = await response.text();
    let parsed: unknown = null;
    try {
      parsed = text ? JSON.parse(text) : null;
    } catch {
      parsed = text;
    }
    return {
      ok: response.ok,
      status: response.status,
      latencyMs,
      data: response.ok ? (parsed as T) : null,
      raw: parsed,
      error: response.ok
        ? undefined
        : `Upstream returned ${response.status}`,
    };
  } catch (err) {
    return {
      ok: false,
      status: 0,
      latencyMs: Math.round(performance.now() - started),
      data: null,
      raw: null,
      error: err instanceof Error ? err.message : "Unknown network error",
    };
  }
}
