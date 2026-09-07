import { Panel, PanelHeader } from "@/components/ui/Panel";
import { MetricCard } from "@/components/MetricCard";
import { LatencyChart } from "@/components/LatencyChart";
import type { LatencyHistoryPoint, TelemetrySnapshot } from "@/types/overwatch";
import type { ProcessingTelemetry } from "@/lib/api";

interface TelemetryProps {
  telemetry: TelemetrySnapshot;
  history: LatencyHistoryPoint[];
  simulationTelemetry?: ProcessingTelemetry | null;
  isIdle?: boolean;
}

export function Telemetry({ telemetry, history, simulationTelemetry, isIdle }: TelemetryProps) {
  const showActive = Boolean(simulationTelemetry) && !isIdle;

  const latencyStr = showActive ? simulationTelemetry!.latency_ms.toFixed(1) : "--";
  const cpuStr = showActive ? `${simulationTelemetry!.cpu_percent.toFixed(0)}` : "--";
  const memStr = showActive ? `${simulationTelemetry!.memory_percent.toFixed(0)}` : "--";
  const fpsStr = showActive ? simulationTelemetry!.frame_rate_fps.toFixed(0) : "--";
  const snrStr = showActive ? `+${simulationTelemetry!.snr_gain_db.toFixed(1)}` : "--";

  const hasPercentiles = Boolean(
    showActive &&
      simulationTelemetry &&
      (simulationTelemetry.p50_latency > 0 || simulationTelemetry.p95_latency > 0)
  );

  return (
    <Panel>
      <PanelHeader
        title="Telemetry"
        eyebrow="SIMULATED & ESTIMATED TELEMETRY — Not measured hardware metrics"
        right={
          <span className="font-data text-[9.5px] text-tertiary px-1.5 py-0.5 rounded border border-line bg-panel uppercase">
            SIMULATION / ESTIMATED MODE
          </span>
        }
      />

      <div className="grid grid-cols-2 md:grid-cols-5 gap-2.5 mb-3.5">
        <MetricCard label="Latency" value={latencyStr} unit={showActive ? "ms" : ""} tone="cyan" />
        <MetricCard label="CPU Load (Sim)" value={cpuStr} unit={showActive ? "%" : ""} />
        <MetricCard label="Memory (Sim)" value={memStr} unit={showActive ? "%" : ""} />
        <MetricCard label="Frame Rate" value={fpsStr} unit={showActive ? "FPS" : ""} />
        <MetricCard
          label="Est. SNR Gain"
          value={snrStr}
          unit={showActive ? "dB" : ""}
          tone="green"
        />
      </div>

      {/* Latency Percentiles Breakdown (P50, P95, P99, MAX) */}
      {hasPercentiles && (
        <div className="grid grid-cols-4 gap-2 mb-3.5 pt-2.5 border-t border-line/60 bg-panel-inset rounded-sm p-2">
          <PercentileStat label="P50 Latency" value={`${simulationTelemetry!.p50_latency.toFixed(1)} ms`} />
          <PercentileStat label="P95 Latency" value={`${simulationTelemetry!.p95_latency.toFixed(1)} ms`} />
          <PercentileStat label="P99 Latency" value={`${simulationTelemetry!.p99_latency.toFixed(1)} ms`} opacity />
          <PercentileStat label="MAX Latency" value={`${simulationTelemetry!.max_latency.toFixed(1)} ms`} alert />
        </div>
      )}

      <div className="pt-3 border-t border-line">
        <div className="flex items-center justify-between mb-1">
          <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase">
            Latency History Trace ({history.length} data points)
          </div>
        </div>
        <LatencyChart data={history} />
      </div>
    </Panel>
  );
}

function PercentileStat({
  label,
  value,
  opacity,
  alert,
}: {
  label: string;
  value: string;
  opacity?: boolean;
  alert?: boolean;
}) {
  return (
    <div className="text-center">
      <div className="text-[9.5px] tracking-[0.05em] text-tertiary font-data uppercase mb-0.5">
        {label}
      </div>
      <div
        className={`font-data text-[12px] font-semibold ${
          alert ? "text-amber" : opacity ? "text-cyan/80" : "text-primary"
        }`}
      >
        {value}
      </div>
    </div>
  );
}
