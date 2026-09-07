"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";
import { SpectrogramChart } from "@/components/SpectrogramChart";
import type { AudioAnalysisResponse } from "@/lib/api";

interface SpectrogramComparisonChartProps {
  original?: AudioAnalysisResponse;
  processed?: AudioAnalysisResponse;
}

export function SpectrogramComparisonChart({
  original,
  processed,
}: SpectrogramComparisonChartProps) {
  if (!original?.spectrogram || !processed?.spectrogram) {
    return null;
  }

  return (
    <Panel>
      <PanelHeader
        title="STFT Spectrogram Comparison"
        eyebrow="Time-Frequency Energy Distribution Shift (Original vs Processed)"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Original Spectrogram */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <span className="font-data text-[10px] text-cyan font-bold tracking-wide uppercase px-1.5 py-0.5 rounded border border-cyan/30 bg-cyan/10">
              ORIGINAL SPECTROGRAM
            </span>
            <span className="font-data text-[10px] text-tertiary">
              {original.metadata.sample_rate / 1000} kHz · {original.metadata.duration}s
            </span>
          </div>
          <SpectrogramChart
            spectrogram={original.spectrogram}
            sampleRateHz={original.metadata.sample_rate}
          />
        </div>

        {/* Processed Spectrogram */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <span className="font-data text-[10px] text-green font-bold tracking-wide uppercase px-1.5 py-0.5 rounded border border-green/30 bg-green/10">
              ENHANCED SPECTROGRAM
            </span>
            <span className="font-data text-[10px] text-tertiary">
              {processed.metadata.sample_rate / 1000} kHz · {processed.metadata.duration}s
            </span>
          </div>
          <SpectrogramChart
            spectrogram={processed.spectrogram}
            sampleRateHz={processed.metadata.sample_rate}
          />
        </div>
      </div>
    </Panel>
  );
}
