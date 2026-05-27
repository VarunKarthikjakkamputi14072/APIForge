"use client";

import { useMemo, useState } from "react";
import { Eye, EyeOff, KeyRound, RotateCw, Trash2 } from "lucide-react";
import { CopyButton } from "./CopyButton";
import { maskKey } from "@/lib/apiKey";

type Props = {
  apiKey: string;
  createdAt: string;
  onRevoke?: () => void;
  onRotate?: () => void;
  className?: string;
};

export function ApiKeyCard({ apiKey, createdAt, onRevoke, onRotate, className = "" }: Props) {
  const [revealed, setRevealed] = useState(false);
  const display = useMemo(() => (revealed ? apiKey : maskKey(apiKey)), [apiKey, revealed]);
  const created = useMemo(() => {
    if (!createdAt) return "—";
    try {
      return new Date(createdAt).toLocaleString();
    } catch {
      return createdAt;
    }
  }, [createdAt]);

  return (
    <section className={`panel ${className}`}>
      <header className="panel-header">
        <div className="flex items-center gap-2">
          <KeyRound className="h-4 w-4 text-terminal-accent" />
          <h3 className="text-sm font-semibold text-slate-100">Primary API key</h3>
          <span className="badge bg-terminal-accentDim/40 text-terminal-accent">
            <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-terminal-accent" />
            active
          </span>
        </div>
        <span className="hidden text-xs text-slate-500 sm:inline">
          created {created}
        </span>
      </header>

      <div className="space-y-4 px-4 py-4">
        <div className="group flex items-center gap-2 rounded-md border border-terminal-border bg-terminal-bg px-3 py-2">
          <span className="mono shrink truncate text-sm text-slate-100" title={apiKey}>
            {display || "—"}
          </span>
          <div className="ml-auto flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setRevealed((v) => !v)}
              className="btn-ghost px-2 py-1.5 text-xs"
              aria-label={revealed ? "Hide key" : "Reveal key"}
            >
              {revealed ? (
                <EyeOff className="h-3.5 w-3.5" />
              ) : (
                <Eye className="h-3.5 w-3.5" />
              )}
              <span>{revealed ? "Hide" : "Reveal"}</span>
            </button>
            <CopyButton value={apiKey} label="Copy" />
          </div>
        </div>

        <div className="grid gap-3 text-xs text-slate-400 sm:grid-cols-3">
          <div>
            <div className="label">Created</div>
            <div className="mono text-slate-200">{created}</div>
          </div>
          <div>
            <div className="label">Prefix</div>
            <div className="mono text-slate-200">{apiKey.slice(0, 10)}…</div>
          </div>
          <div>
            <div className="label">Tier</div>
            <div className="text-slate-200">Free · 100 req/hr</div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-1">
          {onRotate && (
            <button type="button" onClick={onRotate} className="btn-ghost">
              <RotateCw className="h-3.5 w-3.5" />
              Rotate key
            </button>
          )}
          {onRevoke && (
            <button
              type="button"
              onClick={onRevoke}
              className="inline-flex items-center justify-center gap-2 rounded-md border border-red-900/60 bg-transparent px-4 py-2 text-sm font-medium text-red-300 transition hover:border-red-500/80 hover:text-red-200"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Revoke
            </button>
          )}
          <p className="text-xs text-slate-500">
            Treat this key like a password. APIForge stores only an HMAC-SHA256
            hash — we can&apos;t show it again after revocation.
          </p>
        </div>
      </div>
    </section>
  );
}
