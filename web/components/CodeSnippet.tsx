"use client";

import { useMemo, useState } from "react";
import { CopyButton } from "./CopyButton";
import { highlight, type Language } from "@/lib/highlight";

export type CodeTab = {
  label: string;
  language: Language;
  code: string;
};

type Props = {
  tabs: CodeTab[];
  title?: string;
  className?: string;
  defaultTab?: number;
};

export function CodeSnippet({ tabs, title, className = "", defaultTab = 0 }: Props) {
  const [active, setActive] = useState(Math.min(defaultTab, tabs.length - 1));
  const current = tabs[active];

  const highlighted = useMemo(
    () => highlight(current.code.trimEnd(), current.language),
    [current.code, current.language],
  );

  return (
    <div className={`panel overflow-hidden ${className}`}>
      <div className="panel-header gap-3">
        <div className="flex items-center gap-2">
          {title && <span className="text-sm font-semibold text-slate-100">{title}</span>}
          <span className="hidden text-xs text-slate-500 sm:inline">
            {current.label}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <div className="mr-2 hidden items-center gap-0.5 rounded-md border border-terminal-border bg-terminal-bg p-0.5 sm:flex">
            {tabs.map((tab, i) => (
              <button
                key={tab.label + i}
                type="button"
                onClick={() => setActive(i)}
                className={`rounded px-2.5 py-1 text-xs font-medium transition ${
                  i === active
                    ? "bg-terminal-panel text-terminal-accent"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <CopyButton value={current.code} />
        </div>
      </div>
      {/* Mobile tab selector */}
      <div className="border-b border-terminal-border bg-terminal-bg/60 px-3 py-2 sm:hidden">
        <select
          value={active}
          onChange={(e) => setActive(Number(e.target.value))}
          className="input"
        >
          {tabs.map((tab, i) => (
            <option key={tab.label + i} value={i}>
              {tab.label}
            </option>
          ))}
        </select>
      </div>
      <pre className="mono overflow-x-auto bg-terminal-bg/60 px-4 py-3 text-xs leading-relaxed text-slate-200">
        <code>{highlighted}</code>
      </pre>
    </div>
  );
}
