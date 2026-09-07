"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import type { SpectrumPoint } from "@/types/overwatch";

interface SpectrumChartProps {
  data: SpectrumPoint[];
  maxFrequencyHz?: number;
  hasAudio?: boolean;
}

export function SpectrumChart({ data, maxFrequencyHz, hasAudio }: SpectrumChartProps) {
  const isEmpty = !hasAudio || !data || data.length === 0;
  const maxFreq = maxFrequencyHz ?? (data && data.length > 0 ? data[data.length - 1].frequencyHz : 8000);
  const eyebrowText = isEmpty ? "FFT Analysis" : `0 Hz — ${(maxFreq / 1000).toFixed(1)} kHz`;

  return (
    <Panel noPadding className="p-4">
      <PanelHeader title="Frequency Spectrum" eyebrow={eyebrowText} />
      <div className="h-[190px] -ml-2 flex items-center justify-center">
        {isEmpty ? (
          <div className="font-data text-[12px] text-tertiary text-center">
            Upload audio file to view frequency spectrum.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 6, right: 12, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="spectrum-gradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-signal-cyan)" stopOpacity={0.45} />
                  <stop offset="100%" stopColor="var(--color-signal-cyan)" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--color-line)" strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="frequencyHz"
                tickFormatter={(v) => `${(v / 1000).toFixed(1)}k`}
                tick={{ fill: "var(--color-tertiary)", fontSize: 10, fontFamily: "var(--font-data)" }}
                axisLine={{ stroke: "var(--color-line)" }}
                tickLine={false}
                interval={15}
              />
              <YAxis
                tick={{ fill: "var(--color-tertiary)", fontSize: 10, fontFamily: "var(--font-data)" }}
                axisLine={false}
                tickLine={false}
                width={34}
                tickFormatter={(v) => `${v}`}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--color-panel-raised)",
                  border: "1px solid var(--color-line-active)",
                  borderRadius: 2,
                  fontFamily: "var(--font-data)",
                  fontSize: 11,
                }}
                labelFormatter={(v) => `${(Number(v) / 1000).toFixed(2)} kHz`}
                formatter={(value) => [`${value} dB`, "Magnitude"]}
                labelStyle={{ color: "var(--color-secondary)" }}
                itemStyle={{ color: "var(--color-cyan)" }}
              />
              <Area
                type="monotone"
                dataKey="magnitudeDb"
                stroke="var(--color-signal-cyan)"
                strokeWidth={1.25}
                fill="url(#spectrum-gradient)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </Panel>
  );
}
