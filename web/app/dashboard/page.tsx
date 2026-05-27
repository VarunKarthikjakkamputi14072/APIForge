"use client";

import { useMemo } from "react";
import Link from "next/link";
import { ArrowRight, Activity, Gauge, History } from "lucide-react";
import { ApiKeyCard } from "@/components/ApiKeyCard";
import { CodeSnippet } from "@/components/CodeSnippet";
import { UsageChart } from "@/components/UsageChart";
import { useApiKey } from "@/lib/apiKey";
import { mockUsage } from "@/lib/mock";
import { buildLanguageSnippets } from "@/lib/snippets";
import { API_BASE_URL, HAS_LIVE_BACKEND } from "@/lib/api";
import { MOCK_API_KEY } from "@/lib/mock";

export default function DashboardPage() {
  const { apiKey, createdAt, setApiKey, hydrated } = useApiKey();
  const usage = useMemo(() => mockUsage(), []);

  const baseUrlForSnippets = HAS_LIVE_BACKEND ? API_BASE_URL : "https://api.apiforge.dev";

  const weatherSnippets = buildLanguageSnippets({
    baseUrl: baseUrlForSnippets,
    apiKey: apiKey || MOCK_API_KEY,
    path: "/api/weather/Berlin",
  });

  const aggregateSnippets = buildLanguageSnippets({
    baseUrl: baseUrlForSnippets,
    apiKey: apiKey || MOCK_API_KEY,
    path: "/api/aggregate?city=Tokyo&topic=ai",
  });

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <PageHeader
        title="Dashboard"
        subtitle="Your APIForge key, live usage, and copy-paste-ready snippets."
      />

      {!HAS_LIVE_BACKEND && (
        <DemoBanner className="mt-6" />
      )}

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <ApiKeyCard
            apiKey={hydrated ? apiKey : ""}
            createdAt={hydrated ? createdAt : ""}
            onRotate={() => {
              const next =
                "af_" +
                Array.from({ length: 32 }, () =>
                  Math.floor(Math.random() * 16).toString(16),
                ).join("");
              setApiKey(next);
            }}
            onRevoke={() => setApiKey("")}
          />
        </div>
        <div className="grid gap-6">
          <StatCard
            icon={<Activity className="h-4 w-4" />}
            label="Requests today"
            value={usage.today.toLocaleString()}
            footnote={`${usage.week.toLocaleString()} this week`}
          />
          <StatCard
            icon={<Gauge className="h-4 w-4" />}
            label="Remaining this hour"
            value={`${usage.remaining}/${usage.hourly_limit}`}
            footnote="Resets at the top of the next hour"
            tone="accent"
          />
          <StatCard
            icon={<History className="h-4 w-4" />}
            label="Last 24 hours"
            value={`${usage.hourly.reduce((a, b) => a + b.requests, 0)} req`}
            footnote="See the analytics tab for breakdowns"
          />
        </div>
      </div>

      <section className="mt-10 panel">
        <header className="panel-header">
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Usage · last 24h</h3>
            <p className="text-xs text-slate-500">
              Hourly request volume on this API key
            </p>
          </div>
          <Link
            href="/analytics"
            className="text-xs font-medium text-terminal-accent hover:underline"
          >
            Full analytics →
          </Link>
        </header>
        <div className="px-4 py-4">
          <UsageChart data={usage.hourly} />
        </div>
      </section>

      <section className="mt-10">
        <div className="mb-4 flex items-end justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Quick start</h2>
            <p className="text-sm text-slate-400">
              Drop these into your next project. The key is your real key.
            </p>
          </div>
          <Link
            href="/docs"
            className="hidden text-sm text-terminal-accent hover:underline sm:inline-flex items-center gap-1"
          >
            All endpoints <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <CodeSnippet title="GET /api/weather/{city}" tabs={weatherSnippets} />
          <CodeSnippet title="GET /api/aggregate" tabs={aggregateSnippets} />
        </div>
      </section>
    </div>
  );
}

function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className="flex flex-col gap-2">
      <div className="section-title">Console</div>
      <h1 className="text-3xl font-bold tracking-tight text-slate-50">{title}</h1>
      <p className="max-w-2xl text-sm text-slate-400">{subtitle}</p>
    </header>
  );
}

function StatCard({
  icon,
  label,
  value,
  footnote,
  tone = "default",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  footnote?: string;
  tone?: "default" | "accent";
}) {
  return (
    <div className={`panel p-4 ${tone === "accent" ? "shadow-glow" : ""}`}>
      <div className="flex items-center justify-between text-xs uppercase tracking-wider text-slate-400">
        <span>{label}</span>
        <span
          className={
            tone === "accent"
              ? "text-terminal-accent"
              : "text-slate-500"
          }
        >
          {icon}
        </span>
      </div>
      <div className="mt-2 mono text-2xl font-semibold text-slate-50">{value}</div>
      {footnote && <div className="mt-1 text-xs text-slate-500">{footnote}</div>}
    </div>
  );
}

function DemoBanner({ className = "" }: { className?: string }) {
  return (
    <div
      className={`flex flex-wrap items-center justify-between gap-3 rounded-md border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-100 ${className}`}
    >
      <div>
        <strong className="font-semibold">Demo mode.</strong>{" "}
        <span className="text-amber-200/90">
          No <span className="mono">NEXT_PUBLIC_APIFORGE_BASE_URL</span> set —
          showing mocked data. Configure it to drive the live gateway.
        </span>
      </div>
      <a
        href="https://github.com/VarunKarthikjakkamputi14072/APIForge-#quickstart"
        className="text-amber-100 underline-offset-2 hover:underline"
        target="_blank"
        rel="noreferrer"
      >
        Setup guide →
      </a>
    </div>
  );
}
