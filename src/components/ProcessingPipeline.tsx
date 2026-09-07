import { Panel, PanelHeader } from "@/components/ui/Panel";
import { PipelineStage } from "@/components/PipelineStage";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { PipelineStageState, SystemRunState } from "@/types/overwatch";

interface ProcessingPipelineProps {
  stages: PipelineStageState[];
  runState: SystemRunState;
}

export function ProcessingPipeline({ stages, runState }: ProcessingPipelineProps) {
  return (
    <Panel>
      <PanelHeader
        title="Processing Pipeline"
        eyebrow="03 · Signal Chain"
        right={
          <StatusBadge
            label={
              runState === "processing"
                ? "Simulating"
                : runState === "stopped"
                ? "Halted"
                : "Standby"
            }
            tone={runState === "processing" ? "cyan" : runState === "stopped" ? "red" : "neutral"}
            pulse={runState === "processing"}
          />
        }
      />

      {/* Desktop / tablet: horizontal signal chain */}
      <div className="hidden sm:flex items-start overflow-x-auto pb-1 -mx-1 px-1">
        {stages.map((stage, i) => (
          <div key={stage.id} className="flex items-start">
            <PipelineStage stage={stage} index={i} />
            {i < stages.length - 1 && (
              <Connector active={stageIsFlowing(stages, i, runState)} horizontal />
            )}
          </div>
        ))}
      </div>

      {/* Mobile: vertical signal chain */}
      <div className="flex sm:hidden flex-col items-center">
        {stages.map((stage, i) => (
          <div key={stage.id} className="flex flex-col items-center w-full max-w-[160px]">
            <PipelineStage stage={stage} index={i} />
            {i < stages.length - 1 && (
              <Connector active={stageIsFlowing(stages, i, runState)} horizontal={false} />
            )}
          </div>
        ))}
      </div>
    </Panel>
  );
}

function stageIsFlowing(
  stages: PipelineStageState[],
  index: number,
  runState: SystemRunState
): boolean {
  if (runState !== "processing") return false;
  const left = stages[index];
  return left.status === "active" || left.status === "complete";
}

function Connector({ active, horizontal }: { active: boolean; horizontal: boolean }) {
  if (horizontal) {
    return (
      <div className="relative w-6 md:w-9 h-[104px] shrink-0 flex items-center justify-center mt-0">
        <svg width="100%" height="2" className="overflow-visible">
          <line
            x1="0"
            y1="1"
            x2="100%"
            y2="1"
            stroke="var(--color-line-strong)"
            strokeWidth="1.5"
          />
          {active && (
            <line
              x1="0"
              y1="1"
              x2="100%"
              y2="1"
              stroke="var(--color-signal-cyan)"
              strokeWidth="1.5"
              strokeDasharray="4 4"
              className="animate-flow"
            />
          )}
        </svg>
      </div>
    );
  }

  return (
    <div className="relative w-[2px] h-6 shrink-0 flex justify-center">
      <svg width="2" height="100%" className="overflow-visible">
        <line x1="1" y1="0" x2="1" y2="100%" stroke="var(--color-line-strong)" strokeWidth="1.5" />
        {active && (
          <line
            x1="1"
            y1="0"
            x2="1"
            y2="100%"
            stroke="var(--color-signal-cyan)"
            strokeWidth="1.5"
            strokeDasharray="4 4"
            className="animate-flow"
          />
        )}
      </svg>
    </div>
  );
}
