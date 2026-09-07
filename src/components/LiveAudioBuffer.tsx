"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";

interface LiveAudioBufferProps {
  bufferPercent: number;
  overBudget: boolean;
}

export function LiveAudioBuffer({ bufferPercent, overBudget }: LiveAudioBufferProps) {
  const isHigh = bufferPercent > 70;

  return (
    <Panel>
      <PanelHeader title="Audio Buffer &amp; Budget" eyebrow="Streaming Constraints" />

      <div className="flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <span className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase">
            Audio Buffer Model
          </span>
          <span className={`font-data text-[12px] font-bold ${
            isHigh ? "text-amber" : "text-cyan"
          }`}>
            {bufferPercent}% ({isHigh ? "HIGH PRESSURE" : "NORMAL"})
          </span>
        </div>

        {/* Buffer Fill Bar */}
        <div className="h-2 bg-panel-inset rounded-full overflow-hidden border border-line">
          <div
            className={`h-full transition-all duration-200 ${
              isHigh ? "bg-amber" : "bg-cyan"
            }`}
            style={{ width: `${Math.min(100, Math.max(0, bufferPercent))}%` }}
          />
        </div>

        {/* Real-time Budget Status */}
        <div className="pt-2 border-t border-line/60 flex items-center justify-between">
          <span className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase">
            Processing Window Budget
          </span>
          {overBudget ? (
            <span className="font-data text-[10.5px] text-red font-bold uppercase px-2 py-0.5 rounded border border-red/30 bg-red/10 animate-pulse">
              ⚠️ PROCESSING OVER BUDGET
            </span>
          ) : (
            <span className="font-data text-[10.5px] text-green font-medium uppercase px-2 py-0.5 rounded border border-green/30 bg-green/10">
              ✓ WITHIN BUDGET
            </span>
          )}
        </div>
      </div>
    </Panel>
  );
}
