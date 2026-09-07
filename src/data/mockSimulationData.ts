import type {
  AudioFileMeta,
  EdgeDeviceState,
  NoiseAnalysisData,
  NoiseScenario,
  PipelineStageId,
  SystemStatusItem,
  TelemetrySnapshot,
} from "@/types/overwatch";

/**
 * PHASE 1 MOCK DATA
 * -----------------
 * Everything in this file is static/generated for UI demonstration only.
 * In later phases:
 *  - mockAudioFile is replaced by the response of POST /api/upload (Phase 2)
 *  - scenarioAnalysis is replaced by Gemini's structured output (Phase 4)
 *  - baseTelemetry / edge device figures remain simulated (labelled as such)
 *    unless a specific metric becomes genuinely measurable.
 */

export const mockAudioFile: AudioFileMeta | null = null;

export const pipelineStageOrder: { id: PipelineStageId; label: string }[] = [
  { id: "input", label: "Input" },
  { id: "preprocessing", label: "Preprocessing" },
  { id: "noise-analysis", label: "Noise Analysis" },
  { id: "classification", label: "Classification" },
  { id: "adaptive-filter", label: "Adaptive Filter" },
  { id: "ai-enhancement", label: "AI Enhancement" },
  { id: "fusion", label: "Fusion" },
  { id: "output", label: "Output" },
];

export const scenarioLabels: Record<NoiseScenario, string> = {
  stationary: "Stationary",
  "non-stationary": "Non-Stationary",
  impulsive: "Impulsive",
};

export const scenarioAnalysis: Record<NoiseScenario, NoiseAnalysisData> = {
  stationary: {
    noiseType: "stationary",
    confidence: 0.91,
    severity: 0.47,
    characteristics: [
      "Constant spectral profile",
      "Low variance over time",
      "Narrowband hum components",
    ],
    recommendedStrategy: "LMS / NLMS ADAPTIVE FILTER",
  },
  "non-stationary": {
    noiseType: "non-stationary",
    confidence: 0.88,
    severity: 0.65,
    characteristics: [
      "Time-varying spectral profile",
      "Fluctuating energy envelope",
      "Wideband modulation",
    ],
    recommendedStrategy: "KALMAN-TRACKED ADAPTIVE FILTER",
  },
  impulsive: {
    noiseType: "impulsive",
    confidence: 0.942,
    severity: 0.82,
    characteristics: [
      "High transient peaks",
      "Short-duration events",
      "Broadband energy",
    ],
    recommendedStrategy: "HYBRID ADAPTIVE FILTERING",
  },
};

/**
 * Baseline SIMULATED telemetry per scenario. Values shift while a run is
 * "processing" via lib/simulation.ts jitter, not because real hardware is
 * being measured.
 */
export const baseTelemetry: Record<NoiseScenario, TelemetrySnapshot> = {
  stationary: {
    latencyMs: 11.2,
    cpuPercent: 31,
    memoryPercent: 44,
    frameRateFps: 52,
    snrGainDb: 9.6,
  },
  "non-stationary": {
    latencyMs: 13.8,
    cpuPercent: 38,
    memoryPercent: 51,
    frameRateFps: 49,
    snrGainDb: 11.8,
  },
  impulsive: {
    latencyMs: 15.7,
    cpuPercent: 42,
    memoryPercent: 58,
    frameRateFps: 48,
    snrGainDb: 14.4,
  },
};

export const idleTelemetry: TelemetrySnapshot = {
  latencyMs: 0,
  cpuPercent: 4,
  memoryPercent: 18,
  frameRateFps: 0,
  snrGainDb: 0,
};

export const edgeDeviceIdle: EdgeDeviceState = {
  deviceName: "Raspberry Pi 5",
  connection: "online",
  cpuPercent: 6,
  memoryPercent: 21,
  dsp: "idle",
  ai: "idle",
  inferenceEngine: "ONNX Runtime",
};

export function edgeDeviceForTelemetry(t: TelemetrySnapshot): EdgeDeviceState {
  return {
    deviceName: "Raspberry Pi 5",
    connection: "online",
    cpuPercent: Math.min(96, t.cpuPercent + 9),
    memoryPercent: Math.min(96, t.memoryPercent + 6),
    dsp: t.frameRateFps > 0 ? "active" : "idle",
    ai: t.frameRateFps > 0 ? "active" : "idle",
    inferenceEngine: "ONNX Runtime",
  };
}

export function systemStatusFor(running: boolean): SystemStatusItem[] {
  return [
    { label: "Audio Input", status: "ready" },
    { label: "DSP Pipeline", status: running ? "active" : "ready" },
    { label: "AI Engine", status: running ? "active" : "ready" },
    { label: "Telemetry", status: "active" },
    { label: "Edge Device", status: "simulated" },
  ];
}
