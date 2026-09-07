"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";
import { AudioComparisonPlayers } from "@/components/AudioComparisonPlayers";
import { WaveformChart } from "@/components/WaveformChart";
import { MetricsComparisonTable } from "@/components/MetricsComparisonTable";
import { SpectrumComparisonChart } from "@/components/SpectrumComparisonChart";
import { SpectrogramComparisonChart } from "@/components/SpectrogramComparisonChart";
import { getAudioUrl, getProcessedAudioUrl, type AudioComparisonResponse, type GeminiAnalysisData } from "@/lib/api";
import type { WaveformPoint } from "@/types/overwatch";

interface BeforeAfterComparisonProps {
  comparisonData: AudioComparisonResponse | null;
  geminiData?: GeminiAnalysisData | null;
  isProcessing?: boolean;
}

export function BeforeAfterComparison({
  comparisonData,
  geminiData,
  isProcessing,
}: BeforeAfterComparisonProps) {
  if (!comparisonData || comparisonData.status === "no_output" || isProcessing) {
    return (
      <Panel>
        <PanelHeader title="OverWatch Enhancement" eyebrow="06 · Before vs After Comparison" />
        <div className="py-8 flex flex-col items-center justify-center text-center gap-2">
          {isProcessing ? (
            <>
              <div className="w-5 h-5 border-2 border-cyan border-t-transparent rounded-full animate-spin" />
              <span className="text-[12px] font-data text-cyan animate-pulse">
                GENERATING SIMULATED ENHANCED AUDIO &amp; COMPARISON METRICS...
              </span>
            </>
          ) : (
            <>
              <span className="text-[12.5px] font-data text-tertiary">
                Run OverWatch processing simulation to generate output &amp; before/after comparison.
              </span>
            </>
          )}
        </div>
      </Panel>
    );
  }

  if (comparisonData.status === "error") {
    return (
      <Panel>
        <PanelHeader title="OverWatch Enhancement" eyebrow="06 · Before vs After Comparison" />
        <div className="p-4 border border-red/30 bg-red/10 rounded-sm text-[12px] font-data text-red">
          Comparison unavailable: {comparisonData.message || "An unexpected error occurred."}
        </div>
      </Panel>
    );
  }

  const { original, processed, deltas, file_id } = comparisonData;

  const originalUrl = getAudioUrl(file_id);
  const processedUrl = getProcessedAudioUrl(file_id);

  // Convert analysis waveform arrays to WaveformPoint[]
  const origWaveformPoints: WaveformPoint[] = original?.waveform
    ? original.waveform.time.map((t, i) => ({ t, amplitude: original.waveform.amplitude[i] }))
    : [];

  const procWaveformPoints: WaveformPoint[] = processed?.waveform
    ? processed.waveform.time.map((t, i) => ({ t, amplitude: processed.waveform.amplitude[i] }))
    : [];

  const strategyName = geminiData?.recommended_strategy;
  const noiseType = geminiData?.noise_type;
  const confidencePct = geminiData?.confidence ? Math.round(geminiData.confidence * 100) : null;

  const isDeepFilter = comparisonData.engine === "DeepFilterNet" || comparisonData.simulation_mode === "deepfilternet";
  const badgeLabel = isDeepFilter ? "DEEPFILTERNET ENHANCED" : "SIMULATED ENHANCEMENT";
  const badgeStyle = isDeepFilter
    ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10 font-bold uppercase"
    : "text-cyan px-2 py-0.5 rounded border border-cyan/30 bg-cyan/10 font-bold uppercase";

  const origFilename = original?.metadata.filename || `${file_id}.wav`;
  const procFilename = `processed_${origFilename}`;

  return (
    <div className="flex flex-col gap-4">
      {/* Summary Card */}
      <Panel>
        <PanelHeader
          title={isDeepFilter ? "DeepFilterNet Audio Enhancement Result" : "OverWatch Processing Result"}
          eyebrow="Phase 6 · Enhancement Summary"
          right={
            <span className={`font-data text-[10px] px-2 py-0.5 rounded border ${badgeStyle}`}>
              {badgeLabel}
            </span>
          }
        />

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SummaryCard
            label="Gemini Rec. Strategy"
            value={strategyName ? strategyName.replace(/_/g, " ") : "UNAVAILABLE"}
            sub={geminiData ? "AI Recommendation (DeepFilterNet Eng.)" : "Gemini AI Offline"}
            tone={geminiData ? "cyan" : "amber"}
          />
          <SummaryCard
            label="AI Noise Environment"
            value={noiseType ? noiseType.toUpperCase() : "N/A"}
            sub={confidencePct !== null ? `Confidence: ${confidencePct}%` : "Gemini AI Offline"}
            tone="amber"
          />
          <SummaryCard
            label="Est. Noise Reduction"
            value={`~${deltas?.estimated_noise_reduction_pct.toFixed(0) ?? 0}%`}
            sub={isDeepFilter ? "DeepFilterNet Neural Inference" : "Simulated Attenuation"}
            tone="green"
          />
          <SummaryCard
            label="RMS Power Shift"
            value={`${deltas?.rms_change_pct.toFixed(1) ?? 0}%`}
            sub="Genuinely Calculated"
            tone="cyan"
          />
        </div>
      </Panel>

      {/* Audio Players & Sequential Comparison */}
      <AudioComparisonPlayers
        originalUrl={originalUrl}
        processedUrl={processedUrl}
        originalFilename={origFilename}
        processedFilename={procFilename}
        strategy={strategyName || "WIENER_FILTER"}
        isReady={true}
      />

      {/* Waveform Comparison (Input vs Output) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <WaveformChart
          title="Input Waveform (Original)"
          eyebrow="Pre-Processing · Raw Audio Signal"
          data={origWaveformPoints}
          color="cyan"
        />
        <WaveformChart
          title={isDeepFilter ? "Output Waveform (DeepFilterNet Enhanced)" : "Output Waveform (Simulated Output)"}
          eyebrow={isDeepFilter ? "DeepFilterNet 48kHz Neural Enhanced Signal" : "Post-Fusion · Real Transformed Signal"}
          data={procWaveformPoints}
          color="green"
        />
      </div>

      {/* Metrics Comparison Table */}
      <MetricsComparisonTable
        original={original}
        processed={processed}
        deltas={deltas}
      />

      {/* Frequency Spectrum Comparison (FFT) */}
      <SpectrumComparisonChart original={original} processed={processed} />

      {/* STFT Spectrogram Comparison Heatmaps */}
      <SpectrogramComparisonChart original={original} processed={processed} />
    </div>
  );
}

function SummaryCard({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub: string;
  tone: "cyan" | "green" | "amber";
}) {
  const color =
    tone === "green" ? "text-green" : tone === "amber" ? "text-amber" : "text-cyan";

  return (
    <div className="bg-panel-inset border border-line rounded-sm p-3">
      <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase mb-1">
        {label}
      </div>
      <div className={`font-data text-[15px] font-bold uppercase ${color}`}>
        {value}
      </div>
      <div className="text-[10.5px] font-data text-tertiary mt-0.5">{sub}</div>
    </div>
  );
}
