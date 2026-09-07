"use client";

import React from "react";
import type { DeepFilterResult } from "@/lib/api";

export type EnhancementModel = "deepfilternet" | "fullsubnet";

interface DenoiseEngineProps {
  result: DeepFilterResult | null;
  isProcessing: boolean;
  error: string | null;
  hasAudio: boolean;
  selectedModel: EnhancementModel;
  onModelSelect: (model: EnhancementModel) => void;
  onDenoiseStart?: () => void;
}

export function DenoiseEngine({
  result,
  isProcessing,
  error,
  hasAudio,
  selectedModel,
  onModelSelect,
  onDenoiseStart,
}: DenoiseEngineProps) {
  const isDFN = selectedModel === "deepfilternet";
  const modelTitle = isDFN ? "DEEPFILTERNET3" : "FULLSUBNET+";

  const getStatusBadge = () => {
    if (isProcessing) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
          PROCESSING...
        </span>
      );
    }
    if (error || result?.status === "error") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-red-500/10 text-red-400 border border-red-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-red-400"></span>
          ERROR
        </span>
      );
    }
    if (result?.status === "not_installed") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
          NOT INSTALLED
        </span>
      );
    }
    if (result?.status === "success") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          COMPLETE
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
        READY
      </span>
    );
  };

  return (
    <div className="bg-surface/60 border border-line rounded-lg p-4 flex flex-col gap-3 relative overflow-hidden">
      {/* Top Header & Model Selector Tabs */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-cyan-400"></div>
          <h3 className="font-mono text-xs text-primary uppercase tracking-wider font-semibold">
            DENOISING ENGINE · {modelTitle}
          </h3>
        </div>

        {/* Model Selection Tabs */}
        <div className="flex items-center gap-1 bg-surface/80 p-1 border border-line/60 rounded-md">
          <button
            type="button"
            onClick={() => onModelSelect("deepfilternet")}
            disabled={isProcessing}
            className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
              isDFN
                ? "bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40"
                : "text-tertiary hover:text-secondary hover:bg-surface"
            } disabled:opacity-50`}
          >
            DeepFilterNet3 (48kHz)
          </button>
          <button
            type="button"
            onClick={() => onModelSelect("fullsubnet")}
            disabled={isProcessing}
            className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
              !isDFN
                ? "bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40"
                : "text-tertiary hover:text-secondary hover:bg-surface"
            } disabled:opacity-50`}
          >
            FullSubNet+ (16kHz)
          </button>
        </div>

        {getStatusBadge()}
      </div>

      {/* Engine Info Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 py-1">
        <div className="bg-surface/80 border border-line/40 rounded p-2.5">
          <p className="font-mono text-[10px] text-tertiary uppercase tracking-wider">
            ENGINE
          </p>
          <p className="font-mono text-xs text-secondary font-medium mt-0.5">
            {result?.engine || (isDFN ? "DeepFilterNet" : "FullSubNet+")}
          </p>
        </div>
        <div className="bg-surface/80 border border-line/40 rounded p-2.5">
          <p className="font-mono text-[10px] text-tertiary uppercase tracking-wider">
            MODEL VERSION
          </p>
          <p className="font-mono text-xs text-cyan-300 font-medium mt-0.5">
            {result?.model_version || (isDFN ? "DeepFilterNet3" : "FullSubNet_Plus")}
          </p>
        </div>
        <div className="bg-surface/80 border border-line/40 rounded p-2.5">
          <p className="font-mono text-[10px] text-tertiary uppercase tracking-wider">
            SAMPLE RATE
          </p>
          <p className="font-mono text-xs text-secondary font-medium mt-0.5">
            {result?.sample_rate
              ? `${result.sample_rate.toLocaleString()} Hz`
              : isDFN
              ? "48,000 Hz"
              : "16,000 Hz"}
          </p>
        </div>
        <div className="bg-surface/80 border border-line/40 rounded p-2.5">
          <p className="font-mono text-[10px] text-tertiary uppercase tracking-wider">
            LATENCY / TIME
          </p>
          <p className="font-mono text-xs text-emerald-400 font-medium mt-0.5">
            {result?.processing_time_ms ? `${result.processing_time_ms} ms` : "--"}
          </p>
        </div>
      </div>

      {/* Detailed Status or Action */}
      {result?.status === "success" && (
        <div className="bg-emerald-950/20 border border-emerald-500/30 rounded p-3 flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-emerald-400 font-semibold">
              ✓ REAL INFERENCE COMPLETE ({result.engine || (isDFN ? "DeepFilterNet3" : "FullSubNet+")})
            </span>
            <span className="text-tertiary">
              File: {result.output_file || (isDFN ? `processed_${result.file_id}.wav` : `processed_fsn_${result.file_id}.wav`)}
            </span>
          </div>
          <p className="text-[11px] text-secondary font-sans leading-relaxed">
            Audio enhanced using pretrained {result.model_version || (isDFN ? "DeepFilterNet3" : "FullSubNet+")} neural model at {isDFN ? "48kHz" : "16kHz"}.
            Processed WAV ready for before/after comparison.
          </p>
        </div>
      )}

      {(error || result?.status === "error") && (
        <div className="bg-red-950/20 border border-red-500/30 rounded p-3 text-xs font-mono text-red-300">
          <p className="font-semibold text-red-400">{isDFN ? "DeepFilterNet" : "FullSubNet+"} Processing Error:</p>
          <p className="mt-1 text-[11px] font-sans">
            {error || result?.error || "Inference failed."}
          </p>
        </div>
      )}

      {result?.status === "not_installed" && (
        <div className="bg-slate-900/40 border border-slate-700/40 rounded p-3 text-xs font-mono text-slate-400">
          <p className="font-semibold text-slate-300">Environment Setup Required:</p>
          <p className="mt-1 text-[11px] font-sans">
            {isDFN ? (
              <>Run <code className="bg-slate-800 px-1 py-0.5 rounded text-cyan-300">backend/setup_deepfilter.ps1</code> to install DeepFilterNet into <code className="bg-slate-800 px-1 py-0.5 rounded text-cyan-300">.venv-dfn</code>.</>
            ) : (
              <>Run <code className="bg-slate-800 px-1 py-0.5 rounded text-cyan-300">backend/setup_fullsubnet.ps1</code> to configure FullSubNet+ into <code className="bg-slate-800 px-1 py-0.5 rounded text-cyan-300">.venv-fsn</code> and obtain checkpoint.</>
            )}
          </p>
        </div>
      )}

      {!result && !isProcessing && !error && (
        <div className="flex items-center justify-between bg-surface/40 border border-line/30 rounded p-3">
          <p className="text-[11px] text-tertiary font-sans">
            {hasAudio
              ? `Ready for real ${isDFN ? "DeepFilterNet3 (48kHz)" : "FullSubNet+ (16kHz)"} speech enhancement.`
              : `Upload audio to enable ${isDFN ? "DeepFilterNet3" : "FullSubNet+"} denoising engine.`}
          </p>
          {hasAudio && onDenoiseStart && (
            <button
              onClick={onDenoiseStart}
              className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-mono text-xs font-medium rounded transition-colors shadow-sm"
            >
              RUN {isDFN ? "DEEPFILTERNET" : "FULLSUBNET+"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

