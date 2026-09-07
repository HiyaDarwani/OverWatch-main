"use client";

import React from "react";
import type { LiveTelemetry } from "@/lib/api";

interface LiveAudioTelemetryProps {
  telemetry: LiveTelemetry | null;
  isCapturing: boolean;
}

export function LiveAudioTelemetry({ telemetry, isCapturing }: LiveAudioTelemetryProps) {
  return (
    <div className="bg-panel border border-line rounded-md p-4 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
          <h3 className="font-mono text-xs text-primary uppercase tracking-wider font-semibold">
            REAL-TIME MICROPHONE TELEMETRY &amp; PHYSICAL MEASUREMENTS
          </h3>
        </div>
        <span className="font-mono text-[10px] text-tertiary uppercase">
          {isCapturing ? "● STREAMING PCM" : "OFFLINE"}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
        <TelemetryMetricCard
          label="RMS AMPLITUDE"
          value={telemetry ? telemetry.rms.toFixed(4) : "--"}
          unit=""
          color="cyan"
        />
        <TelemetryMetricCard
          label="PEAK AMPLITUDE"
          value={telemetry ? telemetry.peak.toFixed(4) : "--"}
          unit=""
          color="cyan"
        />
        <TelemetryMetricCard
          label="INPUT LEVEL"
          value={telemetry ? `${telemetry.db.toFixed(1)}` : "--"}
          unit="dB"
          color="amber"
        />
        <TelemetryMetricCard
          label="ESTIMATED SNR"
          value={telemetry && telemetry.rms > 0.0001 && telemetry.estimated_snr_db !== undefined ? `${telemetry.estimated_snr_db.toFixed(1)}` : "--"}
          unit="dB"
          sub="ESTIMATED (Noise Floor)"
          color="emerald"
        />
        <TelemetryMetricCard
          label="DOMINANT FREQ"
          value={telemetry ? `${telemetry.dominant_frequency.toFixed(0)}` : "--"}
          unit="Hz"
          color="emerald"
        />
        <TelemetryMetricCard
          label="ZERO CROSSING"
          value={telemetry ? telemetry.zero_crossing_rate.toFixed(4) : "--"}
          unit="rate"
          color="slate"
        />
        <TelemetryMetricCard
          label="SPECTRAL CENTROID"
          value={telemetry ? `${telemetry.spectral_centroid.toFixed(0)}` : "--"}
          unit="Hz"
          color="purple"
        />
        <TelemetryMetricCard
          label="SPECTRAL BANDWIDTH"
          value={telemetry ? `${telemetry.spectral_bandwidth.toFixed(0)}` : "--"}
          unit="Hz"
          color="purple"
        />
        <TelemetryMetricCard
          label="SPECTRAL ROLLOFF"
          value={telemetry ? `${telemetry.spectral_rolloff.toFixed(0)}` : "--"}
          unit="Hz"
          color="purple"
        />
        <TelemetryMetricCard
          label="SPECTRAL FLATNESS"
          value={telemetry ? telemetry.spectral_flatness.toFixed(4) : "--"}
          unit=""
          color="slate"
        />
        <TelemetryMetricCard
          label="ROLLING BUFFER"
          value={telemetry ? `${telemetry.buffer_duration_sec.toFixed(1)}` : "--"}
          unit="sec"
          color="emerald"
        />
      </div>
    </div>
  );
}

function TelemetryMetricCard({
  label,
  value,
  unit,
  sub,
  color,
}: {
  label: string;
  value: string;
  unit: string;
  sub?: string;
  color: "cyan" | "emerald" | "amber" | "purple" | "slate";
}) {
  const textColor =
    color === "emerald"
      ? "text-emerald-400"
      : color === "amber"
      ? "text-amber-400"
      : color === "purple"
      ? "text-purple-300"
      : color === "slate"
      ? "text-slate-300"
      : "text-cyan-300";

  return (
    <div className="bg-surface/80 border border-line/40 rounded p-2.5 flex flex-col justify-between">
      <span className="font-mono text-[9.5px] text-tertiary uppercase tracking-wider">
        {label}
      </span>
      <div className="flex items-baseline gap-1 mt-1">
        <span className={`font-mono text-sm font-bold ${textColor}`}>{value}</span>
        {unit && <span className="font-mono text-[10px] text-tertiary">{unit}</span>}
      </div>
      {sub && <span className="font-mono text-[8.5px] text-tertiary/80 mt-0.5">{sub}</span>}
    </div>
  );
}
