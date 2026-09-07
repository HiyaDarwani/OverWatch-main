"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";
import type { AudioAnalysisResponse } from "@/lib/api";

interface SpectrumComparisonChartProps {
  original?: AudioAnalysisResponse;
  processed?: AudioAnalysisResponse;
}

export function SpectrumComparisonChart({
  original,
  processed,
}: SpectrumComparisonChartProps) {
  if (!original?.spectrum || !processed?.spectrum) {
    return null;
  }

  const origSpectrum = original.spectrum;
  const procSpectrum = processed.spectrum;

  const maxFreq = original.metadata.sample_rate / 2;
  const numBins = Math.min(origSpectrum.frequency.length, procSpectrum.frequency.length);

  // SVG Chart Dimensions
  const svgWidth = 800;
  const svgHeight = 160;
  const margin = { top: 10, right: 15, bottom: 25, left: 35 };
  const graphWidth = svgWidth - margin.left - margin.right;
  const graphHeight = svgHeight - margin.top - margin.bottom;

  // Polyline generator: magnitude_db ranges from -100 to 0 dBFS
  const origPoints = Array.from({ length: numBins })
    .map((_, i) => {
      const f = origSpectrum.frequency[i];
      const db = origSpectrum.magnitude_db[i];
      const x = margin.left + (f / maxFreq) * graphWidth;
      const normDb = Math.max(-100, Math.min(0, db));
      const y = margin.top + graphHeight - ((normDb + 100) / 100) * graphHeight;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  const procPoints = Array.from({ length: numBins })
    .map((_, i) => {
      const f = procSpectrum.frequency[i];
      const db = procSpectrum.magnitude_db[i];
      const x = margin.left + (f / maxFreq) * graphWidth;
      const normDb = Math.max(-100, Math.min(0, db));
      const y = margin.top + graphHeight - ((normDb + 100) / 100) * graphHeight;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  // Grid Ticks
  const freqTicks = [0, maxFreq * 0.25, maxFreq * 0.5, maxFreq * 0.75, maxFreq];
  const dbTicks = [0, -25, -50, -75, -100];

  return (
    <Panel>
      <PanelHeader
        title="Frequency Spectrum Comparison (FFT)"
        eyebrow="Original Raw Spectrum vs Processed Filtered Spectrum"
        right={
          <div className="flex items-center gap-3 font-data text-[10px]">
            <span className="flex items-center gap-1 text-cyan font-medium">
              <span className="w-2.5 h-0.5 bg-cyan rounded" /> ORIGINAL (RAW)
            </span>
            <span className="flex items-center gap-1 text-green font-medium">
              <span className="w-2.5 h-0.5 bg-green rounded" /> PROCESSED (ENHANCED)
            </span>
          </div>
        }
      />

      <div className="relative w-full overflow-hidden bg-panel-inset border border-line rounded-sm p-2">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-auto overflow-visible select-none"
        >
          {/* Grid lines */}
          {dbTicks.map((db) => {
            const y = margin.top + graphHeight - ((db + 100) / 100) * graphHeight;
            return (
              <g key={db}>
                <line
                  x1={margin.left}
                  y1={y}
                  x2={svgWidth - margin.right}
                  y2={y}
                  stroke="var(--color-line-dim, #1e2638)"
                  strokeWidth="1"
                  strokeDasharray="2 2"
                />
                <text
                  x={margin.left - 5}
                  y={y + 3}
                  textAnchor="end"
                  fill="var(--color-text-tertiary, #64748b)"
                  fontSize="9"
                  fontFamily="monospace"
                >
                  {db}dB
                </text>
              </g>
            );
          })}

          {freqTicks.map((f) => {
            const x = margin.left + (f / maxFreq) * graphWidth;
            return (
              <g key={f}>
                <line
                  x1={x}
                  y1={margin.top}
                  x2={x}
                  y2={margin.top + graphHeight}
                  stroke="var(--color-line-dim, #1e2638)"
                  strokeWidth="1"
                  strokeDasharray="2 2"
                />
                <text
                  x={x}
                  y={svgHeight - 5}
                  textAnchor="middle"
                  fill="var(--color-text-tertiary, #64748b)"
                  fontSize="9"
                  fontFamily="monospace"
                >
                  {(f / 1000).toFixed(1)}k
                </text>
              </g>
            );
          })}

          {/* Original Spectrum Line (Cyan) */}
          <polyline
            fill="none"
            stroke="var(--color-signal-cyan, #33d6cd)"
            strokeWidth="1.5"
            strokeOpacity="0.8"
            points={origPoints}
          />

          {/* Processed Spectrum Line (Green) */}
          <polyline
            fill="none"
            stroke="#22c55e"
            strokeWidth="1.8"
            points={procPoints}
          />
        </svg>
      </div>
    </Panel>
  );
}
