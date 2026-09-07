"use client";

import { useEffect, useRef } from "react";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import type { ProcessingLogEvent } from "@/lib/api";

interface ProcessingLogProps {
  logs: ProcessingLogEvent[];
}

const LEVEL_COLORS: Record<ProcessingLogEvent["level"], string> = {
  info: "text-tertiary",
  success: "text-green",
  warn: "text-amber",
  error: "text-red-400",
  INFO: "text-tertiary",
  DSP: "text-blue",
  AI: "text-purple-400",
  SIM: "text-cyan",
  WARN: "text-amber",
  SUCCESS: "text-green",
  HW: "text-cyan font-semibold",
};

export function ProcessingLog({ logs }: ProcessingLogProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll to bottom when new log events arrive
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <Panel>
      <PanelHeader title="Processing Log" eyebrow="05 · Execution Telemetry" />

      <div
        ref={containerRef}
        className="h-[140px] overflow-y-auto font-data text-[11px] bg-panel-inset border border-line rounded-sm p-2.5 space-y-1 scrollbar-thin"
      >
        {logs.length === 0 ? (
          <div className="text-tertiary text-[11px] italic">
            Waiting for simulation initiation...
          </div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="flex items-start gap-2 leading-tight">
              <span className="text-tertiary shrink-0 select-none">{log.time}</span>
              <span
                className={`font-semibold shrink-0 uppercase text-[10px] px-1 py-0.2 rounded border ${
                  log.level === "SUCCESS"
                    ? "border-green/30 bg-green/10 text-green"
                    : log.level === "AI"
                    ? "border-purple-500/30 bg-purple-500/10 text-purple-400"
                    : log.level === "SIM"
                    ? "border-cyan/30 bg-cyan/10 text-cyan"
                    : log.level === "DSP"
                    ? "border-blue/30 bg-blue/10 text-blue"
                    : log.level === "WARN"
                    ? "border-amber/30 bg-amber/10 text-amber"
                    : "border-line bg-panel text-tertiary"
                }`}
              >
                {log.level}
              </span>
              <span className={`flex-1 break-words ${LEVEL_COLORS[log.level]}`}>
                {log.message}
              </span>
            </div>
          ))
        )}
      </div>
    </Panel>
  );
}
