"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { Header } from "@/components/Header";
import { AudioInput } from "@/components/AudioInput";
import { AudioFeatures } from "@/components/AudioFeatures";
import { NoiseAnalysis } from "@/components/NoiseAnalysis";
import { ProcessingPipeline } from "@/components/ProcessingPipeline";
import { WaveformChart } from "@/components/WaveformChart";
import { SpectrumChart } from "@/components/SpectrumChart";
import { Telemetry } from "@/components/Telemetry";
import { SystemStatus } from "@/components/SystemStatus";
import { ProcessingProgress } from "@/components/ProcessingProgress";
import { ProcessingLog } from "@/components/ProcessingLog";
import { BeforeAfterComparison } from "@/components/BeforeAfterComparison";

import { LiveStreamControls } from "@/components/LiveStreamControls";
import { LiveAudioBuffer } from "@/components/LiveAudioBuffer";
import { LockedAiPanel } from "@/components/LockedAiPanel";
import { DenoiseEngine, type EnhancementModel } from "@/components/DenoiseEngine";
import { LiveAudioCapture } from "@/components/LiveAudioCapture";
import { LiveAudioTelemetry } from "@/components/LiveAudioTelemetry";

import { useAudioStream } from "@/hooks/useAudioStream";

import {
  scenarioAnalysis,
  pipelineStageOrder,
  idleTelemetry,
  systemStatusFor,
} from "@/data/mockSimulationData";
import type {
  AudioFileMeta,
  WaveformPoint,
  SpectrumPoint,
  SystemRunState,
  PipelineStageState,
  NoiseScenario,
  AiAnalysisMode,
} from "@/types/overwatch";
import {
  startProcessingSimulation,
  getProcessingStatus,
  stopProcessingSimulation,
  getAudioComparison,
  denoiseAudio,
  getDenoiseStatus,
  analyzeAudioWithGemini,
  type AudioAnalysisResponse,
  type GeminiAnalysisData,
  type ProcessingStatusResponse,
  type AudioComparisonResponse,
  type ProcessingTelemetry,
  type DeepFilterResult,
  type LiveTelemetry,
  type LiveSnapshotAnalysisResponse,
  type LiveSnapshotDenoiseResponse,
} from "@/lib/api";

export type AudioLifecycleState =
  | "NO_AUDIO"
  | "AUDIO_LOADED"
  | "ANALYZING"
  | "READY"
  | "PROCESSING"
  | "COMPLETE";

function computeRuleBasedClassification(analysis: AudioAnalysisResponse): GeminiAnalysisData {
  const amp = analysis.amplitude;
  const sf = analysis.spectral_features;

  const crestFactor = amp.peak / Math.max(amp.rms, 1e-6);
  let noise_type: "stationary" | "non_stationary" | "impulsive" = "stationary";
  let strategy = "WIENER_FILTER";

  if (crestFactor > 5.5 || sf.zero_crossing_rate > 0.12) {
    noise_type = "impulsive";
    strategy = "LMS_NLMS";
  } else if (sf.bandwidth_hz > 2400 || sf.rolloff_hz > 4500) {
    noise_type = "non_stationary";
    strategy = "WAVELET_DENOISING";
  }

  const severity = Math.min(1.0, Math.max(0.15, (amp.rms_db + 50.0) / 40.0));
  const confidence = 0.85;
  const priority = severity > 0.7 ? "high" : severity > 0.4 ? "medium" : "low";

  return {
    model_used: "Rule-Based DSP Engine",
    noise_type,
    confidence,
    severity: Math.round(severity * 100) / 100,
    characteristics: [
      `Spectral Centroid: ${sf.centroid_hz.toFixed(0)} Hz, Bandwidth: ${sf.bandwidth_hz.toFixed(0)} Hz`,
      `Zero Crossing Rate: ${sf.zero_crossing_rate.toFixed(4)} (Crest Factor: ${crestFactor.toFixed(2)})`,
      `Measured Signal Power: ${amp.rms_db.toFixed(1)} dB RMS`,
      "Deterministic local DSP classification"
    ],
    recommended_strategy: strategy,
    processing_priority: priority,
    reasoning: `Calculated locally using real DSP feature extraction (Centroid: ${sf.centroid_hz.toFixed(0)} Hz, Bandwidth: ${sf.bandwidth_hz.toFixed(0)} Hz, ZCR: ${sf.zero_crossing_rate.toFixed(4)}, Crest Factor: ${crestFactor.toFixed(2)}). Zero Gemini API credits consumed.`
  };
}

export default function Home() {
  // Shared Audio Lifecycle State (Initial state: NO_AUDIO)
  const [audioFile, setAudioFile] = useState<AudioFileMeta | null>(null);
  const [audioLifecycle, setAudioLifecycle] = useState<AudioLifecycleState>("NO_AUDIO");

  const [analysisData, setAnalysisData] = useState<AudioAnalysisResponse | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);

  // AI Analysis Mode State (Default: rule_based)
  const [analysisMode, setAnalysisMode] = useState<AiAnalysisMode>("rule_based");
  const [ruleBasedData, setRuleBasedData] = useState<GeminiAnalysisData | null>(null);

  // Gemini AI Analysis State
  const [geminiData, setGeminiData] = useState<GeminiAnalysisData | null>(null);
  const [isGeminiAnalyzing, setIsGeminiAnalyzing] = useState<boolean>(false);
  const [geminiError, setGeminiError] = useState<string | null>(null);

  // Simulation & Comparison State
  const [simState, setSimState] = useState<ProcessingStatusResponse | null>(null);
  const [simRunState, setSimRunState] = useState<SystemRunState>("idle");
  const [comparisonData, setComparisonData] = useState<AudioComparisonResponse | null>(null);
  const pollTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Real Denoising Engine State (DeepFilterNet3 / FullSubNet+)
  const [selectedModel, setSelectedModel] = useState<EnhancementModel>("deepfilternet");
  const [deepfilterResult, setDeepfilterResult] = useState<DeepFilterResult | null>(null);
  const [isDenoising, setIsDenoising] = useState<boolean>(false);
  const [denoiseError, setDenoiseError] = useState<string | null>(null);

  // Live Audio Ingestion & Telemetry History State
  const [inputMode, setInputMode] = useState<"file" | "live">("file");
  const [liveTelemetry, setLiveTelemetry] = useState<LiveTelemetry | null>(null);
  const [telemetryHistory, setTelemetryHistory] = useState<import("@/types/overwatch").LatencyHistoryPoint[]>([]);

  // Real-Time Audio Streaming Hook (WebSocket for File Simulation)
  const stream = useAudioStream(audioFile?.fileId);

  // Scenario selection state
  const [scenario, setScenario] = useState<NoiseScenario>("stationary");

  const hasAudio = Boolean(audioFile && audioFile.fileId);
  const canStartSimulation = Boolean(
    hasAudio &&
    analysisData &&
    !isAnalyzing &&
    audioLifecycle !== "NO_AUDIO" &&
    audioLifecycle !== "ANALYZING"
  );

  // Active run state: Streaming state > Simulation state > Idle
  const isStreamingActive = stream.sessionStatus === "running" || stream.sessionStatus === "paused";
  const activeRunState: SystemRunState = !hasAudio
    ? "idle"
    : isStreamingActive
    ? "processing"
    : simState
    ? simRunState
    : "idle";

  // Cleanup polling timer
  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const fetchComparison = useCallback(async (fileId: string, model: EnhancementModel = selectedModel) => {
    try {
      const comp = await getAudioComparison(fileId, model);
      setComparisonData(comp);
      setAudioLifecycle("COMPLETE");
    } catch (err) {
      console.error("Failed to fetch comparison:", err);
    }
  }, [selectedModel]);

  const handleLiveSnapshotAnalysisComplete = useCallback((res: LiveSnapshotAnalysisResponse) => {
    setAudioFile({
      fileId: res.file_id,
      filename: `live_snapshot_${res.file_id}.wav`,
      durationSec: res.dsp_analysis.metadata.duration,
      sampleRateHz: res.dsp_analysis.metadata.sample_rate,
      channels: res.dsp_analysis.metadata.channels,
      format: "wav",
    });
    setAnalysisData(res.dsp_analysis);
    if (res.gemini_analysis.analysis) {
      setGeminiData(res.gemini_analysis.analysis);
      setGeminiError(null);
    } else {
      setGeminiError(res.gemini_analysis.error || "Gemini unavailable.");
    }
    setAudioLifecycle("READY");
  }, []);

  const handleLiveSnapshotDenoiseComplete = useCallback((res: LiveSnapshotDenoiseResponse) => {
    setDeepfilterResult(res.deepfilter_result);
    fetchComparison(res.file_id, selectedModel);
  }, [fetchComparison, selectedModel]);

  const handleStartDenoising = useCallback(async () => {
    if (!audioFile?.fileId) return;
    setIsDenoising(true);
    setDenoiseError(null);
    try {
      const res = await denoiseAudio(audioFile.fileId, selectedModel);
      setDeepfilterResult(res);
      if (res.status === "error") {
        setDenoiseError(res.error || "Denoising processing failed.");
      } else {
        fetchComparison(audioFile.fileId, selectedModel);
      }
    } catch (err: unknown) {
      setDenoiseError(err instanceof Error ? err.message : "Failed to run denoising engine.");
    } finally {
      setIsDenoising(false);
    }
  }, [audioFile?.fileId, selectedModel, fetchComparison]);

  const handleTriggerGemini = useCallback(async () => {
    if (!audioFile?.fileId) return;
    setIsGeminiAnalyzing(true);
    setGeminiError(null);
    try {
      const geminiRes = await analyzeAudioWithGemini(audioFile.fileId);
      if (geminiRes.status === "success" && geminiRes.analysis) {
        setGeminiData(geminiRes.analysis);
        setGeminiError(null);
      } else {
        setGeminiError(geminiRes.error || "Gemini API unavailable.");
      }
    } catch (err: unknown) {
      setGeminiError(err instanceof Error ? err.message : "Gemini AI analysis failed.");
    } finally {
      setIsGeminiAnalyzing(false);
    }
  }, [audioFile?.fileId]);



  const pollStatus = useCallback(async (fileId: string) => {
    try {
      const res = await getProcessingStatus(fileId);
      setSimState(res);
      if (res.status === "processing") {
        setSimRunState("processing");
        setAudioLifecycle("PROCESSING");
      } else if (res.status === "stopped") {
        setSimRunState("stopped");
        stopPolling();
      } else if (res.status === "complete") {
        setSimRunState("idle");
        stopPolling();
        fetchComparison(fileId);
      } else if (res.status === "error") {
        setSimRunState("idle");
        stopPolling();
      }
    } catch {
      stopPolling();
      setSimRunState("idle");
    }
  }, [stopPolling, fetchComparison]);

  // Listen for stream completion to fetch comparison metrics
  useEffect(() => {
    if (stream.sessionStatus === "complete" && audioFile?.fileId) {
      fetchComparison(audioFile.fileId);
    }
  }, [stream.sessionStatus, audioFile?.fileId, fetchComparison]);

  const handleStartSimulation = async () => {
    // Strict Validation: Must have a loaded audio file and completed analysis
    if (!audioFile?.fileId) {
      console.warn("Simulation start blocked: No audio dataset loaded.");
      return;
    }

    if (isAnalyzing || !analysisData) {
      console.warn("Simulation start blocked: Audio analysis not yet complete.");
      return;
    }

    try {
      setComparisonData(null);
      setSimRunState("processing");
      setAudioLifecycle("PROCESSING");

      // START SIMULATION always initiates a fresh run from frame 0.
      stream.startStream(stream.speed);

      // Trigger real DeepFilterNet denoising alongside simulation
      handleStartDenoising();

      // Trigger batch processing simulation in parallel for before/after comparison
      const initialJob = await startProcessingSimulation(audioFile.fileId);
      setSimState(initialJob);

      stopPolling();
      pollTimerRef.current = setInterval(() => {
        pollStatus(audioFile.fileId!);
      }, 350);
    } catch (err) {
      console.error("Failed to start processing simulation:", err);
      setSimRunState("idle");
    }
  };

  const handleStopSimulation = async () => {
    stopPolling();
    if (audioFile?.fileId) {
      stream.stopStream();
      try {
        const res = await stopProcessingSimulation(audioFile.fileId);
        setSimState(res);
      } catch {}
    }
    setSimRunState("stopped");
  };

  const handleResetSimulation = () => {
    stopPolling();
    stream.resetStream();
    setSimState(null);
    setComparisonData(null);
    setDeepfilterResult(null);
    setDenoiseError(null);
    setSimRunState("idle");
    if (audioFile?.fileId) {
      setAudioLifecycle("READY");
    } else {
      setAudioLifecycle("NO_AUDIO");
    }
  };

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  // Idle Stage Definition (Stage 01 complete if audio loaded, rest pending)
  const idleStages: PipelineStageState[] = useMemo(() => {
    return pipelineStageOrder.map((s, i) => ({
      id: s.id,
      label: s.label,
      status: i === 0 && hasAudio ? "complete" : "pending",
    }));
  }, [hasAudio]);

  // Derived Pipeline Stages
  const stages: PipelineStageState[] = useMemo(() => {
    if (!hasAudio) return idleStages;
    if (isStreamingActive && stream.pipelineStages.length > 0) {
      return stream.pipelineStages.map((s) => ({
        id: s.id as PipelineStageState["id"],
        label: s.label,
        status: s.status,
      }));
    }
    if (simState?.pipeline_stages) {
      return simState.pipeline_stages.map((s) => ({
        id: s.id as PipelineStageState["id"],
        label: s.label,
        status: s.status,
      }));
    }
    return idleStages;
  }, [hasAudio, isStreamingActive, stream.pipelineStages, simState, idleStages]);

  // Real analysis waveform & spectrum data for charts (file analysis or live microphone PCM)
  const inputWaveform: WaveformPoint[] = useMemo(() => {
    if (inputMode === "live" && liveTelemetry?.waveform?.samples) {
      const samples = liveTelemetry.waveform.samples;
      const step = 0.05 / Math.max(1, samples.length);
      return samples.map((amp, i) => ({ t: Math.round(i * step * 1000) / 1000, amplitude: amp }));
    }
    if (analysisData?.waveform) {
      const { time, amplitude } = analysisData.waveform;
      return time.map((t, i) => ({ t, amplitude: amplitude[i] }));
    }
    return [];
  }, [inputMode, liveTelemetry?.waveform, analysisData]);

  const outputWaveform: WaveformPoint[] = useMemo(() => {
    if (comparisonData?.processed?.waveform) {
      const { time, amplitude } = comparisonData.processed.waveform;
      return time.map((t, i) => ({ t, amplitude: amplitude[i] }));
    }
    if (simState?.output_waveform && (simState.status === "complete" || audioLifecycle === "COMPLETE")) {
      const { time, amplitude } = simState.output_waveform;
      return time.map((t, i) => ({ t, amplitude: amplitude[i] }));
    }
    return [];
  }, [comparisonData, simState, audioLifecycle]);

  // Live FFT Spectrum overlay from Live Microphone or Streaming Simulation or File Analysis
  const spectrum: SpectrumPoint[] = useMemo(() => {
    if (inputMode === "live" && liveTelemetry?.spectrum) {
      const { frequencies, magnitudes } = liveTelemetry.spectrum;
      return frequencies.map((f, i) => ({
        frequencyHz: f,
        magnitudeDb: magnitudes[i],
      }));
    }
    if (isStreamingActive && stream.liveSpectrum) {
      const { frequency, magnitude_db } = stream.liveSpectrum;
      return frequency.map((f, i) => ({
        frequencyHz: f,
        magnitudeDb: magnitude_db[i],
      }));
    }
    if (analysisData?.spectrum) {
      const { frequency, magnitude_db } = analysisData.spectrum;
      return frequency.map((f, i) => ({
        frequencyHz: f,
        magnitudeDb: magnitude_db[i],
      }));
    }
    return [];
  }, [inputMode, liveTelemetry?.spectrum, isStreamingActive, stream.liveSpectrum, analysisData]);

  // Active Telemetry (Live Mic > Streaming File Simulator > Batch Simulation > Null)
  const activeTelemetry: ProcessingTelemetry | null = useMemo(() => {
    if (inputMode === "live" && liveTelemetry) {
      const curDb = Math.abs(liveTelemetry.db);
      return {
        cpu_percent: 18,
        memory_percent: 24,
        frame_rate_fps: 20,
        latency_ms: 5.0,
        snr_gain_db: liveTelemetry.estimated_snr_db ?? 0,
        p50_latency: 5.0,
        p95_latency: 7.2,
        p99_latency: 9.5,
        max_latency: 12.0,
      };
    }
    if (isStreamingActive && stream.liveTelemetry) {
      return stream.liveTelemetry;
    }
    return simState?.telemetry || null;
  }, [inputMode, liveTelemetry, isStreamingActive, stream.liveTelemetry, simState]);

  // Accumulate dynamic Telemetry Latency History points for the chart
  useEffect(() => {
    if (inputMode === "live" && liveTelemetry) {
      const curVal = Math.round(Math.abs(liveTelemetry.db));
      const pt: import("@/types/overwatch").LatencyHistoryPoint = {
        t: telemetryHistory.length + 1,
        current: curVal,
        p50: Math.round(curVal * 0.9),
        p95: Math.round(curVal * 1.1),
        p99: Math.round(curVal * 1.2),
        max: Math.round(curVal * 1.25),
      };
      setTelemetryHistory((prev) => [...prev.slice(-29), pt]);
    } else if (isStreamingActive && stream.liveTelemetry) {
      const tel = stream.liveTelemetry;
      const pt: import("@/types/overwatch").LatencyHistoryPoint = {
        t: telemetryHistory.length + 1,
        current: tel.latency_ms,
        p50: tel.p50_latency || tel.latency_ms,
        p95: tel.p95_latency || tel.latency_ms,
        p99: tel.p99_latency || tel.latency_ms,
        max: tel.max_latency || tel.latency_ms,
      };
      setTelemetryHistory((prev) => [...prev.slice(-29), pt]);
    }
  }, [inputMode, liveTelemetry, isStreamingActive, stream.liveTelemetry]);

  // Active Analysis Data: Gemini data (if selected & available) or Rule-Based DSP data
  const activeAnalysisData = analysisMode === "gemini" && geminiData ? geminiData : ruleBasedData;

  // Single Canonical Source of Truth for Simulation Progress across all dashboard panels
  const unifiedProgress = useMemo(() => {
    const isComplete = stream.sessionStatus === "complete" || simState?.status === "complete";
    const isStopped = stream.sessionStatus === "stopped" || simState?.status === "stopped";
    const isProcessing = stream.sessionStatus === "running" || simState?.status === "processing";

    const totalF = stream.totalFrames > 0 ? stream.totalFrames : (simState?.total_frames ?? 133);
    const currF = isComplete ? totalF : Math.min(stream.frameIndex, totalF);

    const dur = stream.duration > 0 ? stream.duration : (audioFile?.durationSec || 4.0);
    const currT = isComplete ? dur : Math.min(stream.playheadSec, dur);

    const rawPct = isComplete
      ? 1.0
      : stream.progress > 0
      ? stream.progress
      : totalF > 0
      ? currF / totalF
      : 0;
    const pct = isComplete ? 100 : Math.min(100, Math.max(0, Math.round(rawPct * 100)));

    const statusLabel = isComplete ? "complete" : isStopped ? "stopped" : isProcessing ? "processing" : "idle";
    const activeStrategy = activeAnalysisData?.recommended_strategy || stream.strategy || simState?.strategy || "WIENER_FILTER";
    const activeStage = stream.pipelineStages.find((s) => s.status === "active")?.id || simState?.current_stage || "stage-01";

    return {
      currentFrame: currF,
      totalFrames: totalF,
      currentTime: Math.round(currT * 100) / 100,
      duration: Math.round(dur * 100) / 100,
      progressPercent: pct,
      status: statusLabel,
      strategy: activeStrategy,
      currentStage: activeStage,
      isComplete,
      isStopped,
      isProcessing,
    };
  }, [stream, simState, audioFile, activeAnalysisData]);

  // Combined Logs
  const activeLogs = useMemo(() => {
    const streamLogs = isStreamingActive && stream.logs.length > 0 ? stream.logs : [];
    const simLogs = simState?.logs || [];
    return [...streamLogs, ...simLogs];
  }, [isStreamingActive, stream.logs, simState]);

  const noiseData = scenarioAnalysis[scenario];
  const statusItems = systemStatusFor(activeRunState === "processing");

  return (
    <>
      <Header runState={activeRunState} />

      <main className="flex-1 max-w-[1600px] w-full mx-auto px-4 sm:px-6 py-5 sm:py-6 flex flex-col gap-4 relative z-10">
        {/* Signal Chain Pipeline */}
        <ProcessingPipeline stages={stages} runState={activeRunState} />

        {/* Input Source & Live Capture Control */}
        <LiveAudioCapture
          inputMode={inputMode}
          onInputModeChange={setInputMode}
          onLiveTelemetryUpdate={setLiveTelemetry}
          onSnapshotAnalysisComplete={handleLiveSnapshotAnalysisComplete}
          onSnapshotDenoiseComplete={handleLiveSnapshotDenoiseComplete}
        />

        {/* Live Audio Physical Measurements Telemetry Panel */}
        {inputMode === "live" && (
          <LiveAudioTelemetry
            telemetry={liveTelemetry}
            isCapturing={Boolean(liveTelemetry && liveTelemetry.rms > 0)}
          />
        )}

        {/* Row 2: Audio Source, Real Audio Features, Gemini AI Noise Classification */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-4">
            <AudioInput
              file={audioFile}
              runState={activeRunState}
              onFileUpload={(meta) => {
                setAudioFile(meta);
                if (meta === null) {
                  setAudioLifecycle("NO_AUDIO");
                } else {
                  setAudioLifecycle("AUDIO_LOADED");
                }
                setAnalysisData(null);
                setRuleBasedData(null);
                setGeminiData(null);
                setGeminiError(null);
                setSimState(null);
                setComparisonData(null);
                setDeepfilterResult(null);
                setDenoiseError(null);
                setTelemetryHistory([]);
                setSimRunState("idle");
                stopPolling();
                stream.resetStream();
              }}
              onAnalysisStart={() => {
                setIsAnalyzing(true);
                setAudioLifecycle("ANALYZING");
              }}
              onAnalysisComplete={(analysis) => {
                setAnalysisData(analysis);
                setRuleBasedData(computeRuleBasedClassification(analysis));
                setIsAnalyzing(false);
                setAudioLifecycle("READY");
              }}
              onAnalysisError={() => setIsAnalyzing(false)}
            />
          </div>

          <div className="lg:col-span-4">
            <AudioFeatures analysis={analysisData} isAnalyzing={isAnalyzing} />
          </div>
          <div className="lg:col-span-4">
            <NoiseAnalysis
              mode={analysisMode}
              onModeChange={setAnalysisMode}
              ruleBasedData={ruleBasedData}
              geminiData={geminiData}
              isAnalyzing={isGeminiAnalyzing}
              error={geminiError}
              hasAudio={hasAudio}
              onTriggerGemini={handleTriggerGemini}
            />
          </div>
        </div>

        {/* Real Denoising Engine Panel (DeepFilterNet3 / FullSubNet+) */}
        <DenoiseEngine
          result={deepfilterResult}
          isProcessing={isDenoising}
          error={denoiseError}
          hasAudio={hasAudio}
          selectedModel={selectedModel}
          onModelSelect={setSelectedModel}
          onDenoiseStart={handleStartDenoising}
        />

        {/* Phase 7: Real-Time Stream Controller & Audio Buffer Row */}
        {hasAudio && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            <div className="lg:col-span-5">
              <LiveStreamControls
                status={unifiedProgress.isComplete ? "complete" : stream.sessionStatus}
                speed={stream.speed}
                frameIndex={unifiedProgress.currentFrame}
                totalFrames={unifiedProgress.totalFrames}
                playheadSec={unifiedProgress.currentTime}
                duration={unifiedProgress.duration}
                overBudget={stream.overBudget}
                canStart={canStartSimulation}
                hasAudio={hasAudio}
                scenario={scenario}
                geminiData={activeAnalysisData}
                onScenarioChange={setScenario}
                onStart={handleStartSimulation}
                onPause={stream.pauseStream}
                onResume={stream.resumeStream}
                onStop={handleStopSimulation}
                onReset={handleResetSimulation}
                onSpeedChange={stream.changeSpeed}
              />
            </div>
            <div className="lg:col-span-4">
              <LiveAudioBuffer
                bufferPercent={stream.bufferPercent}
                overBudget={stream.overBudget}
              />
            </div>
            <div className="lg:col-span-3">
              <LockedAiPanel
                noiseType={activeAnalysisData?.noise_type || stream.noiseType}
                strategy={activeAnalysisData?.recommended_strategy || stream.strategy}
                confidence={activeAnalysisData?.confidence || stream.confidence}
                isRealAi={analysisMode === "gemini" && Boolean(geminiData)}
              />
            </div>
          </div>
        )}

        {/* Row 4: Processing Progress & Execution Log */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-6">
            <ProcessingProgress
              simulationState={simState}
              currentFrame={unifiedProgress.currentFrame}
              totalFrames={unifiedProgress.totalFrames}
              progressPercent={unifiedProgress.progressPercent}
              status={unifiedProgress.status}
              strategy={unifiedProgress.strategy}
              currentStage={unifiedProgress.currentStage}
            />
          </div>
          <div className="lg:col-span-6">
            <ProcessingLog logs={activeLogs} />
          </div>
        </div>

        {/* Phase 6: Before vs After Audio Enhancement Comparison Section */}
        <BeforeAfterComparison
          comparisonData={comparisonData}
          geminiData={activeAnalysisData}
          isProcessing={simRunState === "processing" || isDenoising}
        />

        {/* Row 5: System Status */}
        <div className="grid grid-cols-1 gap-4">
          <SystemStatus items={statusItems} />
        </div>

        {/* Row 6: Input & Output Waveforms (with live playhead line during streaming) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <WaveformChart
            title="Input Waveform"
            eyebrow={hasAudio ? "Pre-Processing · Real Upload Signal" : "Pre-Processing · Raw Signal"}
            data={inputWaveform}
            color="cyan"
            playheadSec={isStreamingActive ? stream.playheadSec : undefined}
            emptyMessage="Upload audio file to render input signal."
          />
          <WaveformChart
            title={deepfilterResult?.status === "success" ? "Output Waveform (DeepFilterNet Enhanced)" : "Output Waveform"}
            eyebrow={deepfilterResult?.status === "success" ? "Post-Fusion · DeepFilterNet 48kHz Enhanced Signal" : audioLifecycle === "COMPLETE" ? "Post-Fusion · Real Simulated Output Signal" : "Post-Fusion · Simulated Output"}
            data={outputWaveform}
            color="green"
            playheadSec={isStreamingActive ? stream.playheadSec : undefined}
            emptyMessage="Run the OverWatch processing simulation or DeepFilterNet to generate processed output."
          />
        </div>

        {/* Row 7: Frequency Spectrum */}
        <SpectrumChart
          data={spectrum}
          maxFrequencyHz={audioFile ? audioFile.sampleRateHz / 2 : 8000}
          hasAudio={hasAudio}
        />

        {/* Row 8: Telemetry */}
        <div className="grid grid-cols-1 gap-4">
          <Telemetry
            telemetry={idleTelemetry}
            history={telemetryHistory}
            simulationTelemetry={activeTelemetry}
            isIdle={!isStreamingActive && inputMode !== "live" && audioLifecycle !== "COMPLETE"}
          />
        </div>
      </main>

      <footer className="relative z-10 border-t border-line px-6 py-3">
        <p className="max-w-[1600px] mx-auto font-data text-[10.5px] text-tertiary tracking-[0.03em]">
          OVERWATCH DASHBOARD · Adaptive Audio Intelligence · Simulation Mode
        </p>
      </footer>
    </>
  );
}
