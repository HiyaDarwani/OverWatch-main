"use client";

import { Panel, PanelHeader } from "@/components/ui/Panel";
import { scenarioLabels } from "@/data/mockSimulationData";
import type { NoiseScenario, SystemRunState } from "@/types/overwatch";
import type { GeminiAnalysisData } from "@/lib/api";
import type { StreamStatus } from "@/hooks/useAudioStream";

interface SimulationControlsProps {
  scenario: NoiseScenario;
  runState: SystemRunState;
  streamStatus?: StreamStatus;
  hasAudio?: boolean;
  canStart?: boolean;
  isAnalyzing?: boolean;
  geminiData?: GeminiAnalysisData | null;
  onScenarioChange: (scenario: NoiseScenario) => void;
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
}

const SCENARIOS: NoiseScenario[] = ["stationary", "non-stationary", "impulsive"];

export function SimulationControls({
  scenario,
  runState,
  streamStatus = "idle",
  hasAudio = false,
  canStart = false,
  isAnalyzing = false,
  geminiData,
  onScenarioChange,
  onStart,
  onStop,
  onReset,
}: SimulationControlsProps) {
  const isRunning = streamStatus === "running" || runState === "processing";
  const isPaused = streamStatus === "paused";
  const isComplete = streamStatus === "complete";

  const aiNoiseType = geminiData?.noise_type;
  const normalizedAi = aiNoiseType === "non_stationary" ? "non-stationary" : aiNoiseType;
  const isMatch = normalizedAi ? normalizedAi === scenario : true;

  // START SIMULATION is available whenever canStart is true (audio+analysis ready).
  // It always means a FRESH start from frame 0 — no prior state required.
  const isStartDisabled = !canStart;

  const startButtonLabel = isRunning
    ? "Restart Simulation"
    : isComplete
    ? "Restart Simulation"
    : "Start Simulation";

  const helperMessage = !hasAudio
    ? "Upload an audio dataset to begin simulation."
    : isAnalyzing
    ? "Analyzing audio — please wait..."
    : null;

  return (
    <Panel>
      <PanelHeader title="Simulation Controls" eyebrow="Scenario &amp; Controller" />

      {/* Signal Scenario Selector vs Gemini AI Detection Comparison */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase">
            Signal Scenario
          </div>
          {geminiData && (
            <div className="text-[10px] font-data text-cyan flex items-center gap-1">
              <span>AI DETECTED:</span>
              <span className="font-semibold uppercase">{normalizedAi}</span>
              {!isMatch && (
                <span className="text-amber text-[9.5px] border border-amber/30 bg-amber/10 px-1 rounded">
                  MISMATCH
                </span>
              )}
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 gap-1.5">
          {SCENARIOS.map((s) => {
            const active = s === scenario;
            return (
              <button
                key={s}
                onClick={() => onScenarioChange(s)}
                disabled={!hasAudio}
                className={`text-left px-3 py-2 rounded-sm border font-data text-[12px] tracking-[0.04em] uppercase transition-colors ${
                  !hasAudio
                    ? "border-line text-tertiary opacity-50 cursor-not-allowed"
                    : active
                    ? "border-cyan text-cyan bg-cyan-dim/30 cursor-pointer"
                    : "border-line text-secondary hover:border-line-active hover:text-primary cursor-pointer"
                }`}
              >
                <span className="flex items-center justify-between">
                  {scenarioLabels[s]}
                  {active && <span className="w-1.5 h-1.5 rounded-full bg-cyan" />}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2 pt-3 border-t border-line">
        <button
          onClick={onStart}
          disabled={isStartDisabled}
          className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-sm bg-cyan/10 border border-cyan text-cyan font-data text-[12px] font-semibold tracking-[0.06em] uppercase hover:bg-cyan/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          <PlayGlyph /> {startButtonLabel}
        </button>

        {helperMessage && !isRunning && (
          <div className="text-[10.5px] font-data text-tertiary text-center tracking-wide py-0.5">
            {helperMessage}
          </div>
        )}

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={onStop}
            disabled={!isRunning && !isPaused}
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
