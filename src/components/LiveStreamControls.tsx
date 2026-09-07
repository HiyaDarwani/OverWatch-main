"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { StreamStatus } from "@/hooks/useAudioStream";
import type { NoiseScenario } from "@/types/overwatch";
import type { GeminiAnalysisData } from "@/lib/api";

interface LiveStreamControlsProps {
  status: StreamStatus;
  speed: number;
  frameIndex: number;
  totalFrames: number;
  playheadSec: number;
  duration: number;
  overBudget: boolean;
  canStart?: boolean;
  hasAudio?: boolean;
  scenario?: NoiseScenario;
  geminiData?: GeminiAnalysisData | null;
  onScenarioChange?: (scenario: NoiseScenario) => void;
  onStart: (speed?: number) => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
  onReset: () => void;
  onSpeedChange: (speed: number) => void;
}

const SPEEDS = [0.5, 1.0, 2.0, 4.0];
const SCENARIOS: NoiseScenario[] = ["stationary", "non-stationary", "impulsive"];

function formatTime(sec: number) {
  if (!sec || isNaN(sec) || !isFinite(sec)) return "0:00.00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  const ms = Math.floor((sec % 1) * 100);
  return `${m}:${s.toString().padStart(2, "0")}.${ms.toString().padStart(2, "0")}`;
}

export function LiveStreamControls({
  status,
  speed,
  frameIndex,
  totalFrames,
  playheadSec,
  duration,
  overBudget,
  canStart = false,
  hasAudio = false,
  scenario,
  geminiData,
  onScenarioChange,
  onStart,
  onPause,
  onResume,
  onStop,
  onReset,
  onSpeedChange,
}: LiveStreamControlsProps) {
  const isRunning = status === "running";
  const isPaused = status === "paused";
  const isComplete = status === "complete";

  const isStartDisabled = !canStart;
  const displayFrames = totalFrames > 0 ? totalFrames : 133;

  const aiNoiseType = geminiData?.noise_type;
  const normalizedAi = aiNoiseType === "non_stationary" ? "non-stationary" : aiNoiseType;
  const isMatch = normalizedAi && scenario ? normalizedAi === scenario : true;

  return (
    <Panel>
      <PanelHeader
        title="Real-Time Simulation Controls"
        eyebrow="07 · Simulated Live Controller"
        right={
          overBudget ? (
            <span className="font-data text-[9.5px] text-red px-1.5 py-0.5 rounded border border-red/30 bg-red/10 animate-pulse font-bold">
              ⚠️ OVER BUDGET
            </span>
          ) : isRunning ? (
            <StatusBadge label={`● SIMULATED LIVE (${speed}x)`} tone="green" pulse />
          ) : isPaused ? (
            <StatusBadge label="Ⅱ PAUSED" tone="amber" />
          ) : isComplete ? (
            <StatusBadge label="✓ COMPLETE" tone="green" />
          ) : (
            <StatusBadge label="READY" tone="cyan" />
          )
        }
      />

      <div className="flex flex-col gap-3">
        {/* Signal Scenario Selector (if props provided) */}
        {scenario && onScenarioChange && (
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase">
                Simulation Scenario (Rule-Based)
              </div>
              {geminiData && (
                <div className="text-[10px] font-data text-cyan flex items-center gap-1">
                  <span>REAL AI:</span>
                  <span className="font-semibold uppercase">{normalizedAi}</span>
                  {!isMatch && (
                    <span className="text-amber text-[9.5px] border border-amber/30 bg-amber/10 px-1 rounded font-bold" title="Simulation scenario differs from Real Gemini AI analysis">
                      SIM DIVERGED
                    </span>
                  )}
                </div>
              )}
            </div>

            <div className="grid grid-cols-3 gap-1.5">
              {SCENARIOS.map((s) => {
                const active = s === scenario;
                return (
                  <button
                    key={s}
                    onClick={() => onScenarioChange(s)}
                    disabled={!hasAudio}
                    className={`py-1 px-1.5 rounded-sm border font-data text-[10.5px] font-semibold tracking-wider uppercase transition-colors ${
                      !hasAudio
                        ? "border-line text-tertiary opacity-40 cursor-not-allowed"
                        : active
                        ? "border-cyan text-cyan bg-cyan/10 cursor-pointer"
                        : "border-line text-tertiary hover:border-line-active hover:text-primary cursor-pointer"
                    }`}
                  >
                    {s}
                  </button>
                );
              })}
            </div>
          </div>
        )}
        {/* Row 1: Simulation Time & Frame Position counter */}
        <div className="flex items-center justify-between bg-panel-inset border border-line rounded-sm p-2.5">
          <div>
            <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase mb-0.5">
              Simulation Time
            </div>
            <div className="font-data text-[15px] text-primary font-bold">
              {formatTime(playheadSec)} / <span className="text-tertiary">{formatTime(duration || 4.0)}</span>
            </div>
          </div>

          <div className="text-right">
            <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase mb-0.5">
              Frame Position
            </div>
            <div className="font-data text-[14px] text-cyan font-semibold">
              {frameIndex} / <span className="text-tertiary">{displayFrames}</span>
            </div>
          </div>
        </div>

        {/* Speed Selector */}
        <div>
          <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase mb-1.5">
            Simulation Speed
          </div>
          <div className="grid grid-cols-4 gap-1.5">
            {SPEEDS.map((s) => {
              const active = speed === s;
              return (
                <button
                  key={s}
                  onClick={() => onSpeedChange(s)}
                  className={`py-1 rounded-sm border font-data text-[11.5px] font-semibold tracking-wider transition-colors cursor-pointer ${
                    active
                      ? "border-cyan text-cyan bg-cyan/10"
                      : "border-line text-tertiary hover:border-line-active hover:text-primary"
                  }`}
                >
                  {s}x
                </button>
              );
            })}
          </div>
        </div>

        {/* Action Controls */}
        <div className="grid grid-cols-1 gap-2 pt-2 border-t border-line">
          {isRunning ? (
            <button
              onClick={onPause}
              className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-sm bg-amber/10 border border-amber text-amber font-data text-[12px] font-semibold tracking-wide uppercase hover:bg-amber/20 transition-colors cursor-pointer"
            >
              <PauseGlyph /> Pause Stream
            </button>
          ) : isPaused ? (
            <button
              onClick={onResume}
              className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-sm bg-cyan/10 border border-cyan text-cyan font-data text-[12px] font-semibold tracking-wide uppercase hover:bg-cyan/20 transition-colors cursor-pointer"
            >
              <PlayGlyph /> Resume Stream
            </button>
          ) : isComplete ? (
            <button
              onClick={() => onStart()}
              disabled={isStartDisabled}
              className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-sm bg-cyan/10 border border-cyan text-cyan font-data text-[12px] font-semibold tracking-wide uppercase hover:bg-cyan/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <PlayGlyph /> Restart Simulation
            </button>
          ) : (
            <>
              <button
                onClick={() => onStart()}
                disabled={isStartDisabled}
                className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-sm bg-cyan/10 border border-cyan text-cyan font-data text-[12px] font-semibold tracking-wide uppercase hover:bg-cyan/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                <PlayGlyph /> Start Simulation
              </button>
              {isStartDisabled && !hasAudio && (
                <div className="text-[10.5px] font-data text-tertiary text-center tracking-wide py-0.5">
                  Upload an audio dataset to begin simulation.
                </div>
              )}
            </>
          )}

          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={onStop}
              disabled={status === "idle" || status === "stopped"}
              className="flex items-center justify-center gap-2 px-3 py-2 rounded-sm border border-line-active text-secondary font-data text-[11.5px] tracking-[0.05em] uppercase hover:text-primary hover:border-line-strong transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <StopGlyph /> Stop
            </button>
            <button
              onClick={onReset}
              disabled={!hasAudio}
              className="flex items-center justify-center gap-2 px-3 py-2 rounded-sm border border-line-active text-secondary font-data text-[11.5px] tracking-[0.05em] uppercase hover:text-primary hover:border-line-strong transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              <ResetGlyph /> Reset
            </button>
          </div>
        </div>
      </div>
    </Panel>
  );
}

function PlayGlyph() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
      <path d="M6 4l14 8-14 8V4z" />
    </svg>
  );
}

function PauseGlyph() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
      <rect x="5" y="4" width="5" height="16" />
      <rect x="14" y="4" width="5" height="16" />
    </svg>
  );
}

function StopGlyph() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
      <rect x="5" y="5" width="14" height="14" />
    </svg>
  );
}

function ResetGlyph() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
      <path
        d="M4 12a8 8 0 1 1 2.4 5.7M4 12V6m0 6h6"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
