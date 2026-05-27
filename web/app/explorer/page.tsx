"use client";

import { useMemo, useState } from "react";
import { Play, Terminal } from "lucide-react";
import { CodeSnippet } from "@/components/CodeSnippet";
import { useApiKey } from "@/lib/apiKey";
import {
  API_BASE_URL,
  HAS_LIVE_BACKEND,
  buildPath,
  callEndpoint,
  type ApiResult,
} from "@/lib/api";
import {
  mockAggregate,
  mockFinance,
  mockNews,
  mockRawUpstream,
  mockWeather,
} from "@/lib/mock";
import type { EndpointId } from "@/lib/types";
import { buildLanguageSnippets } from "@/lib/snippets";

type ParamField = {
  name: string;
  label: string;
  placeholder: string;
  defaultValue: string;
  required?: boolean;
};

const ENDPOINTS: Record<
  EndpointId,
  {
    id: EndpointId;
    method: "GET";
    label: string;
    description: string;
    template: string;
    params: ParamField[];
  }
> = {
  weather: {
    id: "weather",
    method: "GET",
    label: "/api/weather/{city}",
    description:
      "Fetch current weather for a city and normalize to APIForge's unified schema.",
    template: "/api/weather/{city}",
    params: [
      {
        name: "city",
        label: "City",
        placeholder: "Berlin",
        defaultValue: "Berlin",
        required: true,
      },
    ],
  },
  news: {
    id: "news",
    method: "GET",
    label: "/api/news",
    description: "Search recent news articles by topic.",
    template: "/api/news?topic={topic}&limit={limit}",
    params: [
      {
        name: "topic",
        label: "Topic",
        placeholder: "ai",
        defaultValue: "ai",
        required: true,
      },
      {
        name: "limit",
        label: "Limit (1-100)",
        placeholder: "5",
        defaultValue: "5",
      },
    ],
  },
  finance: {
    id: "finance",
    method: "GET",
    label: "/api/finance/quote",
    description: "Fetch a real-time stock quote by ticker symbol.",
    template: "/api/finance/quote?symbol={symbol}",
    params: [
      {
        name: "symbol",
        label: "Symbol",
        placeholder: "AAPL",
        defaultValue: "AAPL",
        required: true,
      },
    ],
  },
  aggregate: {
    id: "aggregate",
    method: "GET",
    label: "/api/aggregate",
    description:
      "Fan-out: fetch weather + news in parallel and return a single combined response.",
    template: "/api/aggregate?city={city}&topic={topic}",
    params: [
      {
        name: "city",
        label: "City",
        placeholder: "Tokyo",
        defaultValue: "Tokyo",
        required: true,
      },
      {
        name: "topic",
        label: "Topic",
        placeholder: "tech",
        defaultValue: "tech",
        required: true,
      },
    ],
  },
};

const ENDPOINT_ORDER: EndpointId[] = ["weather", "news", "finance", "aggregate"];

export default function ExplorerPage() {
  const { apiKey, hydrated } = useApiKey();
  const [selected, setSelected] = useState<EndpointId>("weather");
  const [params, setParams] = useState<Record<string, string>>(() =>
    Object.fromEntries(ENDPOINTS.weather.params.map((p) => [p.name, p.defaultValue])),
  );
  const [normalized, setNormalized] = useState<unknown>(null);
  const [raw, setRaw] = useState<unknown>(null);
  const [meta, setMeta] = useState<{
    status: number;
    latency: number;
    source: "live" | "mock";
    error?: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);

  const endpoint = ENDPOINTS[selected];
  const path = useMemo(() => buildPath(selected, params), [selected, params]);

  const handleSelect = (id: EndpointId) => {
    setSelected(id);
    setParams(
      Object.fromEntries(ENDPOINTS[id].params.map((p) => [p.name, p.defaultValue])),
    );
    setNormalized(null);
    setRaw(null);
    setMeta(null);
  };

  const handleSend = async () => {
    setLoading(true);
    const t0 = performance.now();
    if (HAS_LIVE_BACKEND && apiKey) {
      const result: ApiResult<unknown> = await callEndpoint(selected, params, apiKey);
      setNormalized(result.data ?? result.raw);
      setRaw({ note: "Live mode shows the gateway response only. Run the Python script in /docs to see raw upstream JSON.", gateway_response: result.raw });
      setMeta({
        status: result.status,
        latency: result.latencyMs,
        source: "live",
        error: result.error,
      });
    } else {
      await new Promise((r) => setTimeout(r, 280));
      let mock: unknown;
      switch (selected) {
        case "weather":
          mock = mockWeather(params.city || "Berlin");
          break;
        case "news":
          mock = mockNews(params.topic || "ai", Number(params.limit || 5));
          break;
        case "finance":
          mock = mockFinance(params.symbol || "AAPL");
          break;
        case "aggregate":
          mock = mockAggregate(params.city || "Tokyo", params.topic || "tech");
          break;
      }
      setNormalized(mock);
      setRaw(mockRawUpstream(selected, params));
      setMeta({
        status: 200,
        latency: Math.round(performance.now() - t0),
        source: "mock",
      });
    }
    setLoading(false);
  };

  const baseUrlForSnippets = HAS_LIVE_BACKEND ? API_BASE_URL : "https://api.apiforge.dev";
  const snippets = buildLanguageSnippets({
    baseUrl: baseUrlForSnippets,
    apiKey: hydrated ? apiKey : "af_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    path,
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <header className="flex flex-col gap-2">
        <div className="section-title">Explorer</div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-50">API Explorer</h1>
        <p className="max-w-2xl text-sm text-slate-400">
          Fire requests at the gateway, inspect the normalized response, and
          compare it to what the upstream returned.
        </p>
      </header>

      <div className="mt-8 grid gap-6 lg:grid-cols-[280px,1fr]">
        {/* Endpoint list */}
        <aside className="panel h-fit">
          <div className="panel-header">
            <h2 className="text-sm font-semibold text-slate-100">Endpoints</h2>
          </div>
          <ul className="p-2">
            {ENDPOINT_ORDER.map((id) => {
              const item = ENDPOINTS[id];
              const active = selected === id;
              return (
                <li key={id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(id)}
                    className={`flex w-full flex-col gap-1 rounded-md px-3 py-2 text-left transition ${
                      active
                        ? "bg-terminal-bg ring-1 ring-terminal-accent/50"
                        : "hover:bg-terminal-bg/60"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="badge bg-emerald-500/15 text-emerald-300">
                        {item.method}
                      </span>
                      <span className="mono text-sm text-slate-100">{item.label}</span>
                    </div>
                    <span className="text-xs text-slate-500">{item.description}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        {/* Builder + response */}
        <div className="space-y-6">
          <section className="panel">
            <div className="panel-header">
              <div className="flex items-center gap-2">
                <Terminal className="h-4 w-4 text-terminal-accent" />
                <span className="mono text-sm text-slate-100">
                  GET {path}
                </span>
              </div>
              <button
                type="button"
                onClick={handleSend}
                disabled={loading}
                className="btn-primary"
              >
                <Play className="h-3.5 w-3.5" />
                {loading ? "Sending…" : "Send"}
              </button>
            </div>
            <div className="grid gap-4 p-4 sm:grid-cols-2">
              {endpoint.params.map((p) => (
                <div key={p.name}>
                  <label className="label" htmlFor={p.name}>
                    {p.label}
                    {p.required && (
                      <span className="ml-1 text-terminal-accent">*</span>
                    )}
                  </label>
                  <input
                    id={p.name}
                    value={params[p.name] ?? ""}
                    onChange={(e) =>
                      setParams((prev) => ({ ...prev, [p.name]: e.target.value }))
                    }
                    placeholder={p.placeholder}
                    className="input mono"
                  />
                </div>
              ))}
              <div className="sm:col-span-2">
                <label className="label">X-API-Key</label>
                <input
                  value={hydrated ? apiKey : ""}
                  readOnly
                  className="input mono opacity-80"
                />
              </div>
            </div>
            {meta && (
              <div className="flex flex-wrap items-center gap-3 border-t border-terminal-border px-4 py-2.5 text-xs">
                <StatusBadge status={meta.status} />
                <span className="mono text-slate-300">{meta.latency} ms</span>
                <span className="badge bg-slate-700/40 text-slate-300">
                  source: {meta.source}
                </span>
                {meta.error && (
                  <span className="text-red-300">· {meta.error}</span>
                )}
              </div>
            )}
          </section>

          <div className="grid gap-6 lg:grid-cols-2">
            <ResponsePanel
              title="Normalized response"
              subtitle="APIForge unified schema"
              accent
              value={normalized}
              empty="Send a request to see the normalized JSON."
            />
            <ResponsePanel
              title="Raw upstream response"
              subtitle="What the provider actually returned"
              value={raw}
              empty="Send a request to inspect the raw upstream payload."
            />
          </div>

          <section>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-100">
                Copy this request
              </h2>
              <span className="text-xs text-slate-500">
                Identical to the call &ldquo;Send&rdquo; just made
              </span>
            </div>
            <CodeSnippet tabs={snippets} />
          </section>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: number }) {
  let tone = "bg-slate-700/40 text-slate-300";
  if (status >= 200 && status < 300) tone = "bg-emerald-500/15 text-emerald-300";
  else if (status === 429) tone = "bg-amber-500/20 text-amber-300";
  else if (status >= 400) tone = "bg-red-500/15 text-red-300";
  return <span className={`badge ${tone} mono`}>{status || "ERR"}</span>;
}

function ResponsePanel({
  title,
  subtitle,
  value,
  empty,
  accent = false,
}: {
  title: string;
  subtitle: string;
  value: unknown;
  empty: string;
  accent?: boolean;
}) {
  const pretty = useMemo(() => {
    if (value === null || value === undefined) return "";
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }, [value]);

  return (
    <div className={`panel overflow-hidden ${accent ? "shadow-glow" : ""}`}>
      <div className="panel-header">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">{title}</h3>
          <div className="text-xs text-slate-500">{subtitle}</div>
        </div>
      </div>
      <pre className="mono max-h-[420px] overflow-auto bg-terminal-bg/60 px-4 py-3 text-xs leading-relaxed text-slate-200">
        {pretty || <span className="text-slate-500">{empty}</span>}
      </pre>
    </div>
  );
}
