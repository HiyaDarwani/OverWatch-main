"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";
import type { AudioAnalysisResponse } from "@/lib/api";

interface AudioFeaturesProps {
  analysis: AudioAnalysisResponse | null;
  isAnalyzing?: boolean;
}

export function AudioFeatures({ analysis, isAnalyzing }: AudioFeaturesProps) {
  if (isAnalyzing) {
    return (
      <Panel>
        <PanelHeader title="Audio Features" eyebrow="02 · DSP Measurement" />
        <div className="py-8 flex flex-col items-center justify-center gap-2 text-center">
          <div className="w-5 h-5 border-2 border-cyan border-t-transparent rounded-full animate-spin" />
          <span className="text-[12px] font-data text-cyan animate-pulse">
            ANALYZING DSP FEATURES...
          </span>
        </div>
      </Panel>
    );
  }

  if (!analysis) {
    return (
      <Panel>
        <PanelHeader title="Audio Features" eyebrow="02 · DSP Measurement" />
        <div className="py-6 text-center font-data text-[12px] text-tertiary">
          Upload an audio file to view real DSP measurements.
        </div>
      </Panel>
    );
  }

  const { amplitude, spectral_features, metadata } = analysis;

  return (
    <Panel>
      <PanelHeader
        title="Audio Features"
        eyebrow="02 · DSP Measurement"
        right={
          <span className="font-data text-[10px] text-cyan px-1.5 py-0.5 rounded border border-cyan/30 bg-cyan/10">
            REAL DSP
          </span>
        }
      />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <FeatureCard
          label="RMS Level"
          value={amplitude.rms.toFixed(4)}
          sub={`val (${amplitude.rms_db.toFixed(1)} dB)`}
          tone="cyan"
        />
        <FeatureCard
          label="Peak Level"
          value={amplitude.peak.toFixed(4)}
          sub={`val (${amplitude.peak_dbfs.toFixed(1)} dBFS)`}
          tone="green"
        />
        <FeatureCard
          label="Spectral Centroid"
          value={`${(spectral_features.centroid_hz / 1000).toFixed(2)} kHz`}
          sub={`${spectral_features.centroid_hz.toFixed(0)} Hz`}
          tone="cyan"
        />
        <FeatureCard
          label="Zero Crossing Rate"
          value={spectral_features.zero_crossing_rate.toFixed(4)}
          sub="crossings / sample"
          tone="amber"
        />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 pt-3 border-t border-line font-data">
        <div>
          <div className="text-[10px] tracking-[0.1em] text-tertiary uppercase mb-0.5">
            Spectral Bandwidth
          </div>
          <div className="text-[13px] text-primary font-medium">
            {(spectral_features.bandwidth_hz / 1000).toFixed(2)} kHz
          </div>
        </div>
        <div>
          <div className="text-[10px] tracking-[0.1em] text-tertiary uppercase mb-0.5">
            Spectral Rolloff
          </div>
          <div className="text-[13px] text-primary font-medium">
            {(spectral_features.rolloff_hz / 1000).toFixed(2)} kHz
          </div>
        </div>
        <div className="col-span-2 sm:col-span-1">
          <div className="text-[10px] tracking-[0.1em] text-tertiary uppercase mb-0.5">
            Total Samples
          </div>
          <div className="text-[13px] text-primary font-medium">
            {metadata.num_samples.toLocaleString()}
          </div>
        </div>
      </div>
    </Panel>
  );
}

function FeatureCard({
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
  const textColor =
    tone === "cyan" ? "text-cyan" : tone === "green" ? "text-green" : "text-amber";

  return (
    <div className="bg-panel-inset border border-line rounded-sm p-2.5 flex flex-col justify-between">
      <div className="text-[10px] tracking-[0.08em] text-tertiary font-data uppercase mb-1 truncate" title={label}>
        {label}
      </div>
      <div>
        <div className={`font-data text-[15px] font-semibold ${textColor}`}>{value}</div>
        <div className="font-data text-[10px] text-tertiary truncate">{sub}</div>
      </div>
    </div>
  );
}
