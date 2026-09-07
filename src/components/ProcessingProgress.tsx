"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { ProcessingStatusResponse } from "@/lib/api";

interface ProcessingProgressProps {
  simulationState?: ProcessingStatusResponse | null;
  currentFrame?: number;
  totalFrames?: number;
  progressPercent?: number;
  status?: string;
  strategy?: string;
  currentStage?: string;
}

export function ProcessingProgress({
  simulationState,
  currentFrame,
  totalFrames,
  progressPercent,
  status: statusProp,
  strategy: strategyProp,
  currentStage: currentStageProp,
}: ProcessingProgressProps) {
  const status = statusProp || simulationState?.status || "idle";
  const isIdle = status === "idle" && (currentFrame === undefined || currentFrame === 0);

  if (isIdle) {
    return (
      <Panel>
        <PanelHeader
          title="Processing Progress"
          eyebrow="04 · Frame Simulation"
          right={<StatusBadge label="Standby" tone="neutral" />}
        />
        <div className="py-6 flex flex-col items-center justify-center text-center gap-1.5 text-tertiary font-data">
          <span className="text-[12px]">NO SIMULATION ACTIVE</span>
          <span className="text-[10.5px]">Upload audio and click &quot;Start Simulation&quot; to begin frame-based processing.</span>
        </div>
      </Panel>
    );
  }

  const framesProcessed = currentFrame ?? simulationState?.processed_frames ?? 0;
  const framesTotal = totalFrames ?? simulationState?.total_frames ?? 133;
  const pct = progressPercent !== undefined
    ? progressPercent
    : simulationState?.progress !== undefined
    ? Math.min(100, Math.max(0, Math.round(simulationState.progress * 100)))
    : 0;

  const current_stage = currentStageProp || simulationState?.current_stage || "stage-01";
  const strategy = strategyProp || simulationState?.strategy || "WIENER_FILTER";

  const isProcessing = status === "processing" || status === "running";
  const isComplete = status === "complete";
  const isStopped = status === "stopped" || status === "halted";

  return (
    <Panel>
      <PanelHeader
        title="Processing Progress"
        eyebrow="04 · Frame Simulation"
        right={
          <StatusBadge
            label={isProcessing ? "Processing" : isComplete ? "Complete" : isStopped ? "Halted" : "Error"}
            tone={isProcessing ? "cyan" : isComplete ? "green" : "red"}
            pulse={isProcessing}
          />
        }
      />

      <div className="flex flex-col gap-3">
        {/* Row 1: Frames & Progress % */}
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase mb-0.5">
              Frames Processed
            </div>
            <div className="font-data text-[15px] text-primary font-medium">
              {framesProcessed.toLocaleString()} / <span className="text-tertiary">{framesTotal.toLocaleString()}</span>
            </div>
          </div>

          <div className="text-right">
            <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase mb-0.5">
              Progress
            </div>
            <div className="font-data text-[18px] text-cyan font-bold">
              {pct}%
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="h-2 bg-panel-inset rounded-full overflow-hidden border border-line">
          <div
            className={`h-full transition-all duration-200 ${
              isComplete ? "bg-green" : isStopped ? "bg-red" : "bg-cyan"
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>

        {/* Strategy & Current Stage */}
        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-line">
          <div>
            <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase mb-1">
              Active Strategy
            </div>
            <div className="font-data text-[11.5px] text-cyan bg-cyan/10 border border-cyan/30 rounded-sm px-2 py-0.5 inline-block font-semibold">
              {strategy.replace(/_/g, " ")}
            </div>
          </div>

          <div className="text-right">
            <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase mb-1">
              Current Stage
            </div>
            <div className="font-data text-[11.5px] text-primary bg-panel-inset border border-line rounded-sm px-2 py-0.5 inline-block uppercase font-medium">
              {current_stage.replace("-", " ")}
            </div>
          </div>
        </div>
      </div>
    </Panel>
  );
}
