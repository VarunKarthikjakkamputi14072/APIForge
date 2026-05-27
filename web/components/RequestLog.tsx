"use client";

import type { RequestRecord } from "@/lib/types";

function latencyTone(ms: number): { bg: string; text: string; label: string } {
  if (ms < 200) {
    return { bg: "bg-emerald-500/15", text: "text-emerald-300", label: "fast" };
  }
  if (ms < 500) {
    return { bg: "bg-amber-500/15", text: "text-amber-300", label: "ok" };
  }
  return { bg: "bg-red-500/15", text: "text-red-300", label: "slow" };
}

function statusTone(code: number): { bg: string; text: string } {
  if (code === 0) return { bg: "bg-slate-700/40", text: "text-slate-300" };
  if (code < 300) return { bg: "bg-emerald-500/15", text: "text-emerald-300" };
  if (code === 429) return { bg: "bg-amber-500/20", text: "text-amber-300" };
  if (code < 500) return { bg: "bg-amber-500/15", text: "text-amber-200" };
  return { bg: "bg-red-500/15", text: "text-red-300" };
}

function formatTime(ts: string): string {
  try {
    return new Date(ts).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return ts;
  }
}

export function RequestLogRow({ record }: { record: RequestRecord }) {
  const latency = latencyTone(record.latency_ms);
  const status = statusTone(record.status);
  return (
    <tr className="border-b border-terminal-border/60 last:border-b-0 hover:bg-terminal-panel/50">
      <td className="py-2.5 pl-4 pr-3 align-middle">
        <span className={`badge ${status.bg} ${status.text}`}>{record.status || "ERR"}</span>
      </td>
      <td className="px-3 align-middle">
        <span className="mono text-sm text-slate-100">{record.endpoint}</span>
      </td>
      <td className="px-3 align-middle">
        <span className={`badge ${latency.bg} ${latency.text}`}>
          <span className="mono">{record.latency_ms}ms</span>
          <span className="opacity-70">· {latency.label}</span>
        </span>
      </td>
      <td className="py-2.5 pl-3 pr-4 text-right align-middle">
        <span className="mono text-xs text-slate-400">{formatTime(record.timestamp)}</span>
      </td>
    </tr>
  );
}

export function RequestLogTable({
  records,
  emptyMessage = "No requests yet.",
}: {
  records: RequestRecord[];
  emptyMessage?: string;
}) {
  return (
    <div className="panel overflow-hidden">
      <div className="panel-header">
        <h3 className="text-sm font-semibold text-slate-100">Recent requests</h3>
        <span className="text-xs text-slate-500">{records.length} total</span>
      </div>
      {records.length === 0 ? (
        <div className="px-4 py-10 text-center text-sm text-slate-500">{emptyMessage}</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-terminal-bg/60 text-xs uppercase tracking-wider text-slate-400">
              <tr>
                <th className="py-2.5 pl-4 pr-3 font-semibold">Status</th>
                <th className="px-3 font-semibold">Endpoint</th>
                <th className="px-3 font-semibold">Latency</th>
                <th className="py-2.5 pl-3 pr-4 text-right font-semibold">Time</th>
              </tr>
            </thead>
            <tbody>
              {records.map((r) => (
                <RequestLogRow key={r.id} record={r} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
