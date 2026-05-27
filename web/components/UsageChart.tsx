"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { HourlyPoint } from "@/lib/types";

type Props = {
  data: HourlyPoint[];
  height?: number;
};

export function UsageChart({ data, height = 220 }: Props) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
          <defs>
            <linearGradient id="usage-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22d3a3" stopOpacity={0.45} />
              <stop offset="100%" stopColor="#22d3a3" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#1f2a37" strokeDasharray="3 6" vertical={false} />
          <XAxis
            dataKey="hour"
            stroke="#475569"
            tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "var(--font-mono)" }}
            tickLine={false}
            axisLine={{ stroke: "#1f2a37" }}
            interval={3}
          />
          <YAxis
            stroke="#475569"
            tick={{ fill: "#94a3b8", fontSize: 11, fontFamily: "var(--font-mono)" }}
            tickLine={false}
            axisLine={{ stroke: "#1f2a37" }}
            width={36}
          />
          <Tooltip
            cursor={{ stroke: "#22d3a3", strokeOpacity: 0.3 }}
            contentStyle={{
              background: "#0f151d",
              border: "1px solid #1f2a37",
              borderRadius: 8,
              fontFamily: "var(--font-mono)",
              fontSize: 12,
              color: "#e2e8f0",
            }}
            labelStyle={{ color: "#22d3a3" }}
            formatter={(value: number) => [`${value} req`, "requests"]}
          />
          <Area
            type="monotone"
            dataKey="requests"
            stroke="#22d3a3"
            strokeWidth={2}
            fill="url(#usage-fill)"
            activeDot={{ r: 4, stroke: "#0b1016", strokeWidth: 2 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
