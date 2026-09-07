"use client";

import { AreaChart, Area, YAxis, XAxis, ResponsiveContainer, ReferenceLine } from "recharts";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import type { WaveformPoint } from "@/types/overwatch";

interface WaveformChartProps {
  title: string;
  eyebrow: string;
  data: WaveformPoint[];
  color: "cyan" | "green";
  playheadSec?: number;
  emptyMessage?: string;
}

const STROKE: Record<WaveformChartProps["color"], string> = {
  cyan: "var(--color-signal-cyan)",
  green: "var(--color-signal-green)",
};

export function WaveformChart({ title, eyebrow, data, color, playheadSec, emptyMessage }: WaveformChartProps) {
  const gradientId = `waveform-gradient-${color}`;
  const stroke = STROKE[color];
  const isEmpty = !data || data.length === 0;

  // Compute dynamic max amplitude domain bound so small-signal waveforms fill the chart height
  let maxAbs = 0.01;
  if (!isEmpty) {
    for (let i = 0; i < data.length; i++) {
      const val = data[i]?.amplitude;
      if (typeof val === "number" && Number.isFinite(val)) {
        const absVal = Math.abs(val);
        if (absVal > maxAbs) maxAbs = absVal;
      }
    }
    maxAbs = Math.max(0.01, maxAbs * 1.05);
  }

  return (
    <Panel noPadding className="p-3 pb-2">
      <PanelHeader title={title} eyebrow={eyebrow} />
      <div className="h-[110px] -ml-2 flex items-center justify-center">
        {isEmpty ? (
          <div className="font-data text-[11.5px] text-tertiary text-center px-4">
            {emptyMessage || "No signal data available."}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 4, right: 6, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={stroke} stopOpacity={0.35} />
                  <stop offset="100%" stopColor={stroke} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="t" type="number" hide domain={["dataMin", "dataMax"]} />
              <YAxis domain={[-maxAbs, maxAbs]} hide />
              <ReferenceLine y={0} stroke="var(--color-line)" strokeWidth={1} />
              {playheadSec !== undefined && playheadSec > 0 && (
                <ReferenceLine
                  x={playheadSec}
                  stroke="#33d6cd"
                  strokeWidth={2}
                  strokeDasharray="3 3"
                  label={{
                    value: `${playheadSec.toFixed(1)}s`,
                    position: "top",
                    fill: "#33d6cd",
                    fontSize: 10,
                    fontFamily: "monospace",
                  }}
                />
              )}
              <Area
                type="monotone"
                dataKey="amplitude"
                stroke={stroke}
                strokeWidth={1.25}
                fill={`url(#${gradientId})`}
                isAnimationActive={false}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </Panel>
  );
}
