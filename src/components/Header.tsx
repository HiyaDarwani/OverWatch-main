import { StatusBadge } from "@/components/ui/StatusBadge";
import type { SystemRunState } from "@/types/overwatch";

interface HeaderProps {
  runState: SystemRunState;
}

export function Header({ runState }: HeaderProps) {
  const isProcessing = runState === "processing";

  return (
    <header className="relative z-10 border-b border-line bg-panel/80 backdrop-blur-sm">
      <div className="max-w-[1600px] mx-auto px-6 py-3.5 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Mark />
          <div className="leading-tight">
            <div className="font-display font-bold text-[17px] tracking-[0.02em] text-primary">
              OVERWATCH
            </div>
            <div className="font-data text-[10px] tracking-[0.16em] text-tertiary uppercase">
              Adaptive Audio Intelligence
            </div>
          </div>
        </div>

        <div className="flex items-center gap-5">
          <StatusBadge label="Simulation Mode" tone="amber" pulse />
          <div className="w-px h-6 bg-line hidden sm:block" />
          <div className="hidden sm:flex items-center gap-1.5 font-data text-[11px]">
            <span className="text-tertiary uppercase tracking-[0.06em]">
              System Status ·
            </span>
            <StatusBadge
              label={isProcessing ? "Processing" : "Simulation Ready"}
              tone={isProcessing ? "cyan" : "green"}
              pulse={isProcessing}
            />
          </div>
        </div>
      </div>
    </header>
  );
}

function Mark() {
  return (
    <svg width="30" height="30" viewBox="0 0 30 30" fill="none" aria-hidden="true">
      <rect x="0.5" y="0.5" width="29" height="29" rx="3" stroke="var(--color-line-strong)" />
      <path
        d="M5 15 L9 15 L11 9 L14 21 L16.5 12 L18.5 18 L21 15 L25 15"
        stroke="var(--color-signal-cyan)"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}
