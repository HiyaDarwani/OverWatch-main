// Core domain types for the OverWatch simulation dashboard.
// Phase 1: every value that flows through these types is mock/static data.
// The shapes are designed to match what the real backend (Phases 2-9) will
// eventually return, so UI components will not need to change when mock
// data is swapped for live API responses.

export type NoiseScenario = "stationary" | "non-stationary" | "impulsive";

export type AiAnalysisMode = "rule_based" | "gemini";

export type PipelineStageId =
  | "input"
  | "preprocessing"
  | "noise-analysis"
  | "classification"
  | "adaptive-filter"
  | "ai-enhancement"
  | "fusion"
  | "output";

export type StageStatus = "pending" | "active" | "complete" | "error";

export interface PipelineStageState {
  id: PipelineStageId;
  label: string;
  status: StageStatus;
}

export type SystemRunState = "idle" | "processing" | "stopped";

/** Noise characterization. In later phases this is produced by Gemini. */
export interface NoiseAnalysisData {
  noiseType: NoiseScenario;
  confidence: number; // 0-1
  severity: number; // 0-1
  characteristics: string[];
  recommendedStrategy: string;
}

/** Metadata extracted from uploaded audio file (Phase 2+). */
export interface AudioFileMeta {
  filename: string;
  durationSec: number;
  sampleRateHz: number;
  fileId?: string;
  channels?: number;
  format?: string;
  audioUrl?: string;
}


export type AudioPlaybackStatus = "idle" | "loading" | "ready" | "playing" | "error";

/** A single point in a time-domain waveform trace. Mock-generated in Phase 1. */
export interface WaveformPoint {
  t: number;
  amplitude: number;
}

/** A single point in a frequency-domain spectrum trace. Mock-generated in Phase 1. */
export interface SpectrumPoint {
  frequencyHz: number;
  magnitudeDb: number;
}

/**
 * Telemetry is SIMULATED, not measured hardware performance, until real DSP/ML
 * stages exist. UI copy must make this distinction clear to the viewer.
 */
export interface TelemetrySnapshot {
  latencyMs: number;
  cpuPercent: number;
  memoryPercent: number;
  frameRateFps: number;
  snrGainDb: number;
}

export interface LatencyHistoryPoint {
  t: number;
  current: number;
  p50: number;
  p95: number;
  p99: number;
  max: number;
}

export type EdgeConnectionState = "online" | "offline" | "connecting";
export type EdgeModuleState = "active" | "idle" | "error";

export interface EdgeDeviceState {
  deviceName: string;
  connection: EdgeConnectionState;
  cpuPercent: number;
  memoryPercent: number;
  dsp: EdgeModuleState;
  ai: EdgeModuleState;
  inferenceEngine: string;
}

export type SystemComponentStatus = "ready" | "active" | "simulated" | "offline" | "error";

export interface SystemStatusItem {
  label: string;
  status: SystemComponentStatus;
}
