"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";

interface LockedAiPanelProps {
  noiseType: string;
  strategy: string;
  confidence: number;
  isRealAi?: boolean;
}

export function LockedAiPanel({ noiseType, strategy, confidence, isRealAi = false }: LockedAiPanelProps) {
  const confPct = Math.round(confidence * 100);

  return (
    <Panel>
      <PanelHeader
        title={isRealAi ? "REAL AI DECISION LAYER (GEMINI)" : "SIMULATED DECISION LAYER (RULE-BASED)"}
        eyebrow={isRealAi ? "Session-Locked Real AI Decision" : "Session-Locked Fallback Decision"}
        right={
          isRealAi ? (
            <span className="font-data text-[9.5px] text-cyan px-1.5 py-0.5 rounded border border-cyan/30 bg-cyan/10 uppercase font-bold">
              REAL / GEMINI AI
            </span>
          ) : (
            <span className="font-data text-[9.5px] text-amber px-1.5 py-0.5 rounded border border-amber/30 bg-amber/10 uppercase font-bold">
              SIMULATED / RULE-BASED
            </span>
          )
        }
      />

      <div className="grid grid-cols-3 gap-2 text-center font-data">
        <div className="bg-panel-inset border border-line rounded-sm p-2">
          <div className="text-[9.5px] text-tertiary uppercase mb-0.5">Noise Type</div>
          <div className="text-[12.5px] font-bold text-amber uppercase">{noiseType.replace("_", "-")}</div>
        </div>

        <div className="bg-panel-inset border border-line rounded-sm p-2">
          <div className="text-[9.5px] text-tertiary uppercase mb-0.5" title="Strategy recommended by Gemini AI (DeepFilterNet performs actual neural inference)">
            Gemini Rec. Strategy
          </div>
          <div className="text-[11.5px] font-bold text-cyan uppercase leading-tight mt-0.5">
            {strategy.replace(/_/g, " ")}
          </div>
        </div>

        <div className="bg-panel-inset border border-line rounded-sm p-2">
          <div className="text-[9.5px] text-tertiary uppercase mb-0.5">Confidence</div>
          <div className="text-[12.5px] font-bold text-green">{confPct}%</div>
        </div>
      </div>
    </Panel>
  );
}
