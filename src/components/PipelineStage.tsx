import type { PipelineStageState } from "@/types/overwatch";

interface PipelineStageProps {
  stage: PipelineStageState;
  index: number;
}

const STATUS_STYLES: Record<
  PipelineStageState["status"],
  { border: string; text: string; bg: string; ring: string }
> = {
  pending: {
    border: "border-line",
    text: "text-tertiary",
    bg: "bg-panel-inset",
    ring: "",
  },
  active: {
    border: "border-cyan",
    text: "text-cyan",
    bg: "bg-cyan-dim/40",
    ring: "shadow-[0_0_0_3px_rgba(51,214,205,0.12)]",
  },
  complete: {
    border: "border-green/40",
    text: "text-green",
    bg: "bg-panel-inset",
    ring: "",
  },
  error: {
    border: "border-red",
    text: "text-red",
    bg: "bg-red-dim/30",
    ring: "shadow-[0_0_0_3px_rgba(229,82,90,0.12)]",
  },
};

export function PipelineStage({ stage, index }: PipelineStageProps) {
  const s = STATUS_STYLES[stage.status];

  return (
    <div className="flex flex-col items-center gap-2 w-[104px] shrink-0">
      <div
        className={`relative w-full aspect-square rounded-sm border ${s.border} ${s.bg} ${s.ring} flex flex-col items-center justify-center gap-1 transition-all duration-300`}
      >
        <span className="absolute top-1.5 left-1.5 font-data text-[9px] text-tertiary">
          {String(index + 1).padStart(2, "0")}
        </span>
        {stage.status === "active" && (
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-cyan animate-pulse-dot" />
        )}
        {stage.status === "complete" && (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="text-green">
            <path
              d="M5 13l4 4L19 7"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
        {stage.status === "error" && (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="text-red">
            <path
              d="M12 8v5M12 16.5h.01M4.5 19h15L12 4 4.5 19z"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
        {stage.status === "pending" && (
          <span className="w-2 h-2 rounded-full border border-tertiary" />
        )}
      </div>
      <div className={`text-center font-data text-[10px] tracking-[0.05em] uppercase leading-tight ${s.text}`}>
        {stage.label}
      </div>
    </div>
  );
}
