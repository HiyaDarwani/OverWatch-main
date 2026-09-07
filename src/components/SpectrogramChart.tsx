"use client";

import { useEffect, useRef } from "react";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import type { AudioAnalysisResponse } from "@/lib/api";

interface SpectrogramChartProps {
  spectrogram: AudioAnalysisResponse["spectrogram"] | null;
  sampleRateHz?: number;
}

export function SpectrogramChart({ spectrogram, sampleRateHz }: SpectrogramChartProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    if (!spectrogram || !spectrogram.magnitude_db || spectrogram.magnitude_db.length === 0) {
      // Draw placeholder state
      ctx.fillStyle = "rgba(10, 15, 26, 0.8)";
      ctx.fillRect(0, 0, width, height);
      ctx.fillStyle = "rgba(120, 140, 165, 0.4)";
      ctx.font = "11px var(--font-data), monospace";
      ctx.textAlign = "center";
      ctx.fillText("Upload audio file to render real STFT spectrogram", width / 2, height / 2);
      return;
    }

    const matrix = spectrogram.magnitude_db; // 2D array: [freq_row][time_col]
    const numFreqBins = matrix.length;
    const numTimeSteps = matrix[0].length;

    const cellWidth = width / numTimeSteps;
    const cellHeight = height / numFreqBins;

    // Draw STFT heatmap matrix (Y-axis inverted so high frequencies are at top)
    for (let f = 0; f < numFreqBins; f++) {
      // Invert row index so frequency 0 is at bottom
      const yPos = height - (f + 1) * cellHeight;

      for (let t = 0; t < numTimeSteps; t++) {
        const rawDb = matrix[f][t]; // e.g. -80 to 0 dB
        const valDb = Number.isFinite(rawDb) ? rawDb : -80;
        const xPos = t * cellWidth;

        // Map dB value (-80 dB to 0 dB) to normalized 0..1 range
        const norm = Math.max(0, Math.min(1, (valDb + 80) / 80));

        // Custom Cyber Heatmap color mapping (dark blue -> purple -> cyan -> yellow)
        let r = 0, g = 0, b = 0;
        if (norm < 0.25) {
          // 0.0 - 0.25: Dark Blue to Deep Purple
          const factor = norm / 0.25;
          r = Math.floor(15 * factor);
          g = Math.floor(10 * factor);
          b = Math.floor(40 + 80 * factor);
        } else if (norm < 0.6) {
          // 0.25 - 0.6: Deep Purple to Bright Cyan
          const factor = (norm - 0.25) / 0.35;
          r = Math.floor(15 + 20 * factor);
          g = Math.floor(10 + 200 * factor);
          b = Math.floor(120 + 135 * factor);
        } else if (norm < 0.85) {
          // 0.6 - 0.85: Bright Cyan to Warm Amber
          const factor = (norm - 0.6) / 0.25;
          r = Math.floor(35 + 220 * factor);
          g = Math.floor(210 - 20 * factor);
          b = Math.floor(255 - 200 * factor);
        } else {
          // 0.85 - 1.0: Warm Amber to Bright White-Yellow
          const factor = (norm - 0.85) / 0.15;
          r = 255;
          g = Math.floor(190 + 65 * factor);
          b = Math.floor(55 + 200 * factor);
        }

        ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
        ctx.fillRect(xPos, yPos, cellWidth + 0.5, cellHeight + 0.5);
      }
    }
  }, [spectrogram]);

  const maxFreqHz = spectrogram && spectrogram.frequency.length > 0
    ? spectrogram.frequency[spectrogram.frequency.length - 1]
    : (sampleRateHz ? sampleRateHz / 2 : 8000);

  const durationSec = spectrogram && spectrogram.time.length > 0
    ? spectrogram.time[spectrogram.time.length - 1]
    : 0;

  return (
    <Panel noPadding className="p-4">
      <PanelHeader
        title="STFT Spectrogram"
        eyebrow={`Time-Frequency Intensity · Max ${ (maxFreqHz / 1000).toFixed(1) } kHz`}
        right={
          spectrogram ? (
            <div className="flex items-center gap-1.5 font-data text-[10px] text-tertiary">
              <span>-80 dB</span>
              <div className="w-12 h-2 rounded-sm bg-gradient-to-r from-[#0f0a28] via-[#14c8ff] to-[#fff037] border border-line" />
              <span>0 dB</span>
            </div>
          ) : null
        }
      />

      <div className="relative h-[180px] w-full mt-2 bg-panel-inset border border-line rounded-sm overflow-hidden flex">
        {/* Y-axis labels (Frequency) */}
        <div className="w-11 h-full py-1 px-1 flex flex-col justify-between text-right border-r border-line bg-panel shrink-0 font-data text-[9.5px] text-tertiary">
          <span>{(maxFreqHz / 1000).toFixed(1)}k</span>
          <span>{(maxFreqHz / 2000).toFixed(1)}k</span>
          <span>0 Hz</span>
        </div>

        {/* Spectrogram Canvas */}
        <div className="flex-1 h-full relative">
          <canvas
            ref={canvasRef}
            width={600}
            height={180}
            className="w-full h-full object-fill block"
          />

          {/* Time axis footer overlay */}
          <div className="absolute bottom-0 left-0 right-0 h-4 bg-panel/80 border-t border-line/60 px-2 flex justify-between items-center font-data text-[9.5px] text-tertiary">
            <span>0.0 s</span>
            <span>{(durationSec / 2).toFixed(1)} s</span>
            <span>{durationSec.toFixed(1)} s</span>
          </div>
        </div>
      </div>
    </Panel>
  );
}
