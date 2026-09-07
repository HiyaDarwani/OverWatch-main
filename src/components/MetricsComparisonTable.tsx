"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";
import type { AudioAnalysisResponse, ComparisonDeltas } from "@/lib/api";

interface MetricsComparisonTableProps {
  original?: AudioAnalysisResponse;
  processed?: AudioAnalysisResponse;
  deltas?: ComparisonDeltas;
}

export function MetricsComparisonTable({
  original,
  processed,
  deltas,
}: MetricsComparisonTableProps) {
  if (!original || !processed || !deltas) {
    return (
      <Panel>
        <PanelHeader title="Metrics Comparison" eyebrow="DSP Feature Shift" />
        <div className="py-6 flex flex-col items-center justify-center text-center text-tertiary font-data text-[12px]">
          Waiting for processing simulation completion...
        </div>
      </Panel>
    );
  }

  const origAmp = original.amplitude;
  const procAmp = processed.amplitude;
  const origSpec = original.spectral_features;
  const procSpec = processed.spectral_features;

  const rows = [
    {
      label: "RMS Amplitude",
      orig: origAmp.rms.toFixed(4),
      proc: procAmp.rms.toFixed(4),
      delta: `${deltas.rms_change_pct > 0 ? "+" : ""}${deltas.rms_change_pct.toFixed(1)}%`,
      tone: deltas.rms_change_pct <= 0 ? "green" : "neutral",
    },
    {
      label: "RMS Power (dB)",
      orig: `${origAmp.rms_db.toFixed(1)} dB`,
      proc: `${procAmp.rms_db.toFixed(1)} dB`,
      delta: `${(procAmp.rms_db - origAmp.rms_db).toFixed(1)} dB`,
      tone: procAmp.rms_db <= origAmp.rms_db ? "green" : "neutral",
    },
    {
      label: "Peak Amplitude",
      orig: origAmp.peak.toFixed(4),
      proc: procAmp.peak.toFixed(4),
      delta: `${deltas.peak_change_pct > 0 ? "+" : ""}${deltas.peak_change_pct.toFixed(1)}%`,
      tone: deltas.peak_change_pct <= 0 ? "green" : "neutral",
    },
    {
      label: "Spectral Centroid",
      orig: `${origSpec.centroid_hz.toFixed(0)} Hz`,
      proc: `${procSpec.centroid_hz.toFixed(0)} Hz`,
      delta: `${deltas.centroid_shift_hz > 0 ? "+" : ""}${deltas.centroid_shift_hz.toFixed(0)} Hz`,
      tone: "cyan",
    },
    {
      label: "Spectral Bandwidth",
      orig: `${origSpec.bandwidth_hz.toFixed(0)} Hz`,
      proc: `${procSpec.bandwidth_hz.toFixed(0)} Hz`,
      delta: `${deltas.bandwidth_shift_hz > 0 ? "+" : ""}${deltas.bandwidth_shift_hz.toFixed(0)} Hz`,
      tone: "cyan",
    },
    {
      label: "Spectral Rolloff",
      orig: `${origSpec.rolloff_hz.toFixed(0)} Hz`,
      proc: `${procSpec.rolloff_hz.toFixed(0)} Hz`,
      delta: `${deltas.rolloff_shift_hz > 0 ? "+" : ""}${deltas.rolloff_shift_hz.toFixed(0)} Hz`,
      tone: "cyan",
    },
    {
      label: "Zero Crossing Rate",
      orig: origSpec.zero_crossing_rate.toFixed(4),
      proc: procSpec.zero_crossing_rate.toFixed(4),
      delta: `${deltas.zcr_shift > 0 ? "+" : ""}${deltas.zcr_shift.toFixed(4)}`,
      tone: "neutral",
    },
  ];

  return (
    <Panel>
      <PanelHeader
        title="Metrics Comparison"
        eyebrow="Genuinely Calculated DSP Feature Shift"
        right={
          <span className="font-data text-[9.5px] text-green px-1.5 py-0.5 rounded border border-green/30 bg-green/10 uppercase font-medium">
            REAL MEASUREMENTS
          </span>
        }
      />

      <div className="overflow-x-auto">
        <table className="w-full text-left font-data text-[12px]">
          <thead>
            <tr className="border-b border-line text-[10px] tracking-[0.1em] text-tertiary uppercase">
              <th className="py-2 px-2 font-medium">Feature</th>
              <th className="py-2 px-2 font-medium">Original</th>
              <th className="py-2 px-2 font-medium">Processed</th>
              <th className="py-2 px-2 font-medium text-right">Delta / Shift</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line/60">
            {rows.map((r, i) => (
              <tr key={i} className="hover:bg-panel-inset/50 transition-colors">
                <td className="py-2 px-2 text-secondary font-medium">{r.label}</td>
                <td className="py-2 px-2 text-tertiary">{r.orig}</td>
                <td className="py-2 px-2 text-primary font-semibold">{r.proc}</td>
                <td className="py-2 px-2 text-right">
                  <span
                    className={`px-1.5 py-0.5 rounded border text-[11px] font-semibold ${
                      r.tone === "green"
                        ? "text-green border-green/30 bg-green/10"
                        : r.tone === "cyan"
                        ? "text-cyan border-cyan/30 bg-cyan/10"
                        : "text-secondary border-line bg-panel-inset"
                    }`}
                  >
                    {r.delta}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
