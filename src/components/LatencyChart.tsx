"use client";

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import type { LatencyHistoryPoint } from "@/types/overwatch";

interface LatencyChartProps {
  data: LatencyHistoryPoint[];
}

const SERIES: { key: keyof Omit<LatencyHistoryPoint, "t">; color: string; label: string }[] = [
  { key: "current", color: "var(--color-signal-cyan)", label: "Current" },
  { key: "p50", color: "var(--color-signal-green)", label: "P50" },
  { key: "p95", color: "var(--color-signal-amber)", label: "P95" },
  { key: "p99", color: "var(--color-signal-red)", label: "P99" },
  { key: "max", color: "var(--color-tertiary)", label: "Max" },
];

export function LatencyChart({ data }: LatencyChartProps) {
  return (
    <div>
      <div className="h-[140px] -ml-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
            <XAxis dataKey="t" hide />
            <YAxis
              tick={{ fill: "var(--color-tertiary)", fontSize: 10, fontFamily: "var(--font-data)" }}
              axisLine={false}
              tickLine={false}
              width={30}
              unit="ms"
            />
            <Tooltip
              contentStyle={{
                background: "var(--color-panel-raised)",
                border: "1px solid var(--color-line-active)",
                borderRadius: 2,
                fontFamily: "var(--font-data)",
                fontSize: 11,
              }}
              labelFormatter={() => "Frame"}
              labelStyle={{ color: "var(--color-secondary)" }}
            />
            {SERIES.map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                stroke={s.color}
                strokeWidth={s.key === "current" ? 1.5 : 1}
                dot={false}
                isAnimationActive={false}
                strokeDasharray={s.key === "current" ? undefined : "3 3"}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2">
        {SERIES.map((s) => (
          <div key={s.key} className="flex items-center gap-1">
            <span className="w-2 h-[2px]" style={{ backgroundColor: s.color }} />
            <span className="font-data text-[10px] text-tertiary uppercase tracking-[0.05em]">
              {s.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
