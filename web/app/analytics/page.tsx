"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { UsageChart } from "@/components/UsageChart";
import { RequestLogTable } from "@/components/RequestLog";
import { mockUsage } from "@/lib/mock";

const BAR_COLORS = ["#22d3a3", "#38bdf8", "#a78bfa", "#f472b6"];

export default function AnalyticsPage() {
  const usage = useMemo(() => mockUsage(), []);

  const avgLatency = useMemo(() => {
    if (usage.recent.length === 0) return 0;
    return Math.round(
      usage.recent.reduce((a, b) => a + b.latency_ms, 0) / usage.recent.length,
    );
  }, [usage.recent]);

  const errorRate = useMemo(() => {
    if (usage.recent.length === 0) return 0;
    const errors = usage.recent.filter((r) => r.status >= 400).length;
    return Math.round((errors / usage.recent.length) * 100);
  }, [usage.recent]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <header className="flex flex-col gap-2">
        <div className="section-title">Analytics</div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-50">
          Traffic & latency
        </h1>
        <p className="max-w-2xl text-sm text-slate-400">
          A live view of your API usage. Demo data is shown below — wire up the
          backend to populate from <span className="mono">request_logs</span>.
        </p>
      </header>

      <section className="mt-8 grid gap-4 sm:grid-cols-4">
        <Stat label="Requests today" value={usage.today.toLocaleString()} />
        <Stat label="This week" value={usage.week.toLocaleString()} />
        <Stat label="Avg latency" value={`${avgLatency} ms`} />
        <Stat label="Error rate" value={`${errorRate}%`} tone={errorRate > 5 ? "warn" : "default"} />
      </section>

      <section className="mt-8 grid gap-6 lg:grid-cols-3">
        <div className="panel lg:col-span-2">
          <header className="panel-header">
            <div>
              <h2 className="text-sm font-semibold text-slate-100">
                Requests over time
              </h2>
              <p className="text-xs text-slate-500">Hourly volume · last 24h</p>
            </div>
          </header>
          <div className="px-4 py-4">
            <UsageChart data={usage.hourly} height={280} />
          </div>
        </div>

        <div className="panel">
          <header className="panel-header">
            <div>
              <h2 className="text-sm font-semibold text-slate-100">
                Requests by endpoint
              </h2>
              <p className="text-xs text-slate-500">Last 7 days</p>
            </div>
          </header>
          <div className="px-2 py-4">
            <div style={{ width: "100%", height: 280 }}>
              <ResponsiveContainer>
                <BarChart data={usage.by_endpoint} margin={{ top: 8, right: 16, left: -8, bottom: 8 }}>
                  <CartesianGrid stroke="#1f2a37" strokeDasharray="3 6" vertical={false} />
                  <XAxis
                    dataKey="endpoint"
                    tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "var(--font-mono)" }}
                    tickLine={false}
                    axisLine={{ stroke: "#1f2a37" }}
                    interval={0}
                    angle={-25}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis
                    tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "var(--font-mono)" }}
                    tickLine={false}
                    axisLine={{ stroke: "#1f2a37" }}
                    width={32}
                  />
                  <Tooltip
                    cursor={{ fill: "rgba(34,211,163,0.07)" }}
                    contentStyle={{
                      background: "#0f151d",
                      border: "1px solid #1f2a37",
                      borderRadius: 8,
                      fontFamily: "var(--font-mono)",
                      fontSize: 12,
                      color: "#e2e8f0",
                    }}
                    formatter={(value: number) => [`${value} req`, "requests"]}
                  />
                  <Bar dataKey="requests" radius={[6, 6, 0, 0]}>
                    {usage.by_endpoint.map((_, index) => (
                      <Cell key={index} fill={BAR_COLORS[index % BAR_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </section>

      <section className="mt-8">
        <RequestLogTable records={usage.recent} />
      </section>
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "warn";
}) {
  return (
    <div className="panel p-4">
      <div className="text-xs uppercase tracking-wider text-slate-400">{label}</div>
      <div
        className={`mt-2 mono text-2xl font-semibold ${
          tone === "warn" ? "text-amber-300" : "text-slate-50"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
