"use client";

import { useState } from "react";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import type { AiAnalysisMode, NoiseAnalysisData } from "@/types/overwatch";
import type { GeminiAnalysisData } from "@/lib/api";

interface NoiseAnalysisProps {
  mode: AiAnalysisMode;
  onModeChange: (mode: AiAnalysisMode) => void;
  ruleBasedData?: GeminiAnalysisData | null;
  geminiData?: GeminiAnalysisData | null;
  isAnalyzing?: boolean;
  error?: string | null;
  hasAudio?: boolean;
  onTriggerGemini?: () => void;
  mockData?: NoiseAnalysisData;
}

const TONE_BY_TYPE = {
  stationary: "blue",
  non_stationary: "amber",
  "non-stationary": "amber",
  impulsive: "red",
} as const;

export function NoiseAnalysis({
  mode,
  onModeChange,
  ruleBasedData,
  geminiData,
  isAnalyzing,
  error,
  hasAudio,
  onTriggerGemini,
}: NoiseAnalysisProps) {
  const [showReasoning, setShowReasoning] = useState(true);

  const isRuleBased = mode === "rule_based";

  return (
    <Panel>
      <PanelHeader
        title={isRuleBased ? "RULE-BASED DSP ANALYSIS" : geminiData ? "REAL AI ANALYSIS — GEMINI" : "AI ANALYSIS MODE"}
        eyebrow={isRuleBased ? "03 · Local Acoustic Classification" : "03 · Gemini AI Acoustic Intelligence"}
        right={
          isRuleBased ? (
            <span className="font-data text-[9.5px] text-amber px-1.5 py-0.5 rounded border border-amber/30 bg-amber/10 font-bold uppercase">
              RULE-BASED DSP (LOCAL)
            </span>
          ) : geminiData ? (
            <span className="font-data text-[9.5px] text-cyan px-1.5 py-0.5 rounded border border-cyan/30 bg-cyan/10 font-bold uppercase">
              REAL / GEMINI AI ({geminiData.model_used || "Gemini 3.6 Flash"})
            </span>
          ) : (
            <span className="font-data text-[9.5px] text-cyan px-1.5 py-0.5 rounded border border-cyan/30 bg-cyan/10 font-bold uppercase">
              REAL AI — GEMINI
            </span>
          )
        }
      />

      {/* ─── AI ANALYSIS MODE TOGGLE CONTROL ─────────────────────────────────── */}
      <div className="mb-3.5 pb-3 border-b border-line">
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="font-data text-[10px] text-tertiary uppercase tracking-wider font-semibold">
            AI ANALYSIS MODE
          </span>
          <div className="inline-flex rounded p-0.5 bg-panel-inset border border-line">
            <button
              onClick={() => onModeChange("rule_based")}
              className={`px-2.5 py-1 text-[11px] font-data font-semibold rounded transition-colors cursor-pointer ${
                mode === "rule_based"
                  ? "bg-amber text-black shadow-sm"
                  : "text-secondary hover:text-primary"
              }`}
            >
              RULE-BASED DSP
            </button>
            <button
              onClick={() => onModeChange("gemini")}
              className={`px-2.5 py-1 text-[11px] font-data font-semibold rounded transition-colors cursor-pointer ${
                mode === "gemini"
                  ? "bg-cyan text-black shadow-sm"
                  : "text-secondary hover:text-primary"
              }`}
            >
              REAL AI — GEMINI
            </button>
          </div>
        </div>

        {/* Mode Distinction Subtext Banner */}
        {mode === "rule_based" ? (
          <div className="border border-amber/30 bg-amber/10 rounded px-2.5 py-1.5 flex items-center justify-between">
            <span className="font-data text-[11px] text-amber font-bold tracking-wide uppercase">
              RULE-BASED DSP
            </span>
            <span className="font-data text-[10px] text-amber/90 font-medium">
              LOCAL ANALYSIS • NO GEMINI API USAGE
            </span>
          </div>
        ) : (
          <div className="border border-cyan/30 bg-cyan/10 rounded px-2.5 py-1.5 flex items-center justify-between">
            <span className="font-data text-[11px] text-cyan font-bold tracking-wide uppercase">
              REAL AI — GEMINI
            </span>
            <span className="font-data text-[10px] text-cyan/90 font-medium">
              USES GEMINI API CREDITS
            </span>
          </div>
        )}
      </div>

      {!hasAudio && (
        <div className="py-6 text-center font-data text-[12px] text-tertiary">
          Upload an audio file to view acoustic classification.
        </div>
      )}

      {/* ─── 1. RULE-BASED DSP MODE CONTENT ─────────────────────────────────── */}
      {hasAudio && mode === "rule_based" && (
        <AnalysisDataView
          data={ruleBasedData || defaultRuleData}
          isRuleBased={true}
          showReasoning={showReasoning}
          onToggleReasoning={() => setShowReasoning(!showReasoning)}
        />
      )}

      {/* ─── 2. REAL AI GEMINI MODE CONTENT ─────────────────────────────────── */}
      {hasAudio && mode === "gemini" && (
        <>
          {isAnalyzing ? (
            <div className="py-8 flex flex-col items-center justify-center gap-2 text-center">
              <div className="w-5 h-5 border-2 border-cyan border-t-transparent rounded-full animate-spin" />
              <span className="text-[12px] font-data text-cyan animate-pulse">
                ANALYZING ACOUSTIC ENVIRONMENT (GEMINI)...
              </span>
              <span className="text-[10.5px] font-data text-tertiary">
                Uploading audio &amp; calling Gemini 3.6 Flash model API
              </span>
            </div>
          ) : geminiData ? (
            <AnalysisDataView
              data={geminiData}
              isRuleBased={false}
              showReasoning={showReasoning}
              onToggleReasoning={() => setShowReasoning(!showReasoning)}
            />
          ) : (
            <div className="py-4 flex flex-col gap-3">
              {error && (
                <div className="border border-red-500/40 bg-red-500/10 rounded p-2.5 flex flex-col gap-1">
                  <div className="font-data text-[11px] text-red-400 font-bold tracking-wide uppercase">
                    AI ANALYSIS UNAVAILABLE — GEMINI
                  </div>
                  <div className="font-data text-[11px] text-tertiary leading-tight">
                    {error}
                  </div>
                </div>
              )}

              {error && ruleBasedData && (
                <div className="mt-1">
                  <div className="text-[10px] font-data text-amber uppercase font-bold mb-1.5">
                    RULE-BASED FALLBACK
                  </div>
                  <AnalysisDataView
                    data={ruleBasedData}
                    isRuleBased={true}
                    showReasoning={showReasoning}
                    onToggleReasoning={() => setShowReasoning(!showReasoning)}
                  />
                </div>
              )}

              {!error && (
                <div className="p-4 bg-panel-inset border border-line rounded flex flex-col items-center text-center gap-3">
                  <div className="text-[12px] font-data text-secondary">
                    Gemini AI analysis has not been run for this file yet.
                  </div>
                  <button
                    onClick={onTriggerGemini}
                    className="px-4 py-2 bg-cyan text-black font-data font-bold text-[12px] rounded hover:bg-cyan/90 transition-colors cursor-pointer shadow-md"
                  >
                    ANALYZE WITH GEMINI
                  </button>
                  <div className="text-[10.5px] font-data text-tertiary">
                    This will send audio data to Gemini API and consume credits.
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </Panel>
  );
}

function AnalysisDataView({
  data,
  isRuleBased,
  showReasoning,
  onToggleReasoning,
}: {
  data: GeminiAnalysisData;
  isRuleBased: boolean;
  showReasoning: boolean;
  onToggleReasoning: () => void;
}) {
  const rawType = data.noise_type;
  const tone = TONE_BY_TYPE[rawType] || "blue";
  const typeLabel = rawType === "non_stationary" ? "NON-STATIONARY" : rawType.toUpperCase();

  const priorityTone =
    data.processing_priority === "high"
      ? "text-red border-red/30 bg-red/10"
      : data.processing_priority === "medium"
      ? "text-amber border-amber/30 bg-amber/10"
      : "text-green border-green/30 bg-green/10";

  return (
    <>
      <div className="mb-3.5">
        <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase mb-1">
          {isRuleBased ? "Rule-Based Noise Environment" : "Detected Noise Environment"}
        </div>
        <div
          className={`font-display font-semibold text-[22px] tracking-[0.02em] uppercase ${
            tone === "blue" ? "text-blue" : tone === "amber" ? "text-amber" : "text-red"
          }`}
        >
          {typeLabel} {isRuleBased ? "(RULE-BASED)" : ""}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-3.5">
        <MetricBar
          label={isRuleBased ? "DSP CONFIDENCE" : "AI CONFIDENCE"}
          value={data.confidence}
          tone={isRuleBased ? "amber" : "cyan"}
        />
        <MetricBar label="SEVERITY" value={data.severity} tone={tone} />
      </div>

      <div className="mb-3.5">
        <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase mb-1.5">
          {isRuleBased ? "Rule-Based Characteristics" : "Acoustic Characteristics"}
        </div>
        <ul className="space-y-1">
          {data.characteristics.map((c, i) => (
            <li key={i} className="flex items-start gap-1.5 text-[12px] text-secondary leading-snug font-data">
              <span className={isRuleBased ? "text-amber mt-[2px] shrink-0" : "text-cyan mt-[2px] shrink-0"}>▸</span>
              {c}
            </li>
          ))}
        </ul>
      </div>

      <div className="pt-3 border-t border-line flex flex-col gap-2.5">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase mb-1">
              Recommended Strategy
            </div>
            <div className="font-data text-[12px] text-primary bg-panel-inset border border-line rounded-sm px-2.5 py-1 inline-block font-medium">
              {data.recommended_strategy.replace(/_/g, " ")}
            </div>
          </div>

          <div className="text-right">
            <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase mb-1">Priority</div>
            <span className={`font-data text-[10.5px] px-2 py-0.5 rounded border uppercase font-medium ${priorityTone}`}>
              {data.processing_priority}
            </span>
          </div>
        </div>

        {/* Reasoning Accordion */}
        <div className="pt-2 border-t border-line/60">
          <button
            onClick={onToggleReasoning}
            className="flex items-center justify-between w-full text-[10.5px] font-data text-tertiary hover:text-cyan transition-colors cursor-pointer"
          >
            <span className="tracking-wider uppercase font-semibold">
              {isRuleBased ? "Rule-Based Classification Engine" : "Gemini Reasoning Engine"}
            </span>
            <span>{showReasoning ? "▲" : "▼"}</span>
          </button>

          {showReasoning && (
            <div className="mt-1.5 font-data text-[11.5px] text-secondary bg-panel-inset border border-line rounded-sm p-2.5 leading-relaxed">
              {data.reasoning}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

function MetricBar({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "cyan" | "blue" | "amber" | "red" | "gray";
}) {
  const barColor =
    tone === "cyan"
      ? "bg-cyan"
      : tone === "blue"
      ? "bg-blue"
      : tone === "amber"
      ? "bg-amber"
      : tone === "red"
      ? "bg-red"
      : "bg-line";

  const pct = Math.min(100, Math.max(0, value * 100));

  return (
    <div>
      <div className="flex justify-between items-baseline mb-1">
        <span className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase">{label}</span>
        <span className="font-data text-[12.5px] text-primary font-medium">{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 bg-panel-inset rounded-full overflow-hidden border border-line">
        <div className={`h-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

const defaultRuleData: GeminiAnalysisData = {
  model_used: "Rule-Based DSP Engine",
  noise_type: "stationary",
  confidence: 0.85,
  severity: 0.45,
  characteristics: [
    "Spectral Centroid & Bandwidth analyzed locally",
    "Continuous spectral energy profile",
    "Zero Gemini API credits consumed"
  ],
  recommended_strategy: "WIENER_FILTER",
  processing_priority: "medium",
  reasoning: "Calculated locally from extracted Phase 3 DSP features. Zero Gemini API credits consumed."
};
