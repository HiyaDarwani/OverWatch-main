"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  getLiveWebSocketUrl,
  analyzeLiveSnapshot,
  denoiseLiveSnapshot,
  type LiveTelemetry,
  type LiveSessionStatus,
  type LiveSnapshotAnalysisResponse,
  type LiveSnapshotDenoiseResponse,
} from "@/lib/api";

interface LiveAudioCaptureProps {
  inputMode: "file" | "live";
  onInputModeChange: (mode: "file" | "live") => void;
  onLiveTelemetryUpdate?: (telemetry: LiveTelemetry) => void;
  onSnapshotAnalysisComplete?: (res: LiveSnapshotAnalysisResponse) => void;
  onSnapshotDenoiseComplete?: (res: LiveSnapshotDenoiseResponse) => void;
}

export function LiveAudioCapture({
  inputMode,
  onInputModeChange,
  onLiveTelemetryUpdate,
  onSnapshotAnalysisComplete,
  onSnapshotDenoiseComplete,
}: LiveAudioCaptureProps) {
  const [status, setStatus] = useState<LiveSessionStatus>("idle");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sampleRate, setSampleRate] = useState<number>(48000);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [latestTelemetry, setLatestTelemetry] = useState<LiveTelemetry | null>(null);

  // Snapshot action state
  const [isAnalyzingSnapshot, setIsAnalyzingSnapshot] = useState<boolean>(false);
  const [isDenoisingSnapshot, setIsDenoisingSnapshot] = useState<boolean>(false);
  const [snapshotSuccessMsg, setSnapshotSuccessMsg] = useState<string | null>(null);

  // Web Audio & WebSocket References
  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const scriptNodeRef = useRef<ScriptProcessorNode | null>(null);

  // Clean up Web Audio & WebSocket on unmount
  const stopCapture = useCallback(() => {
    if (scriptNodeRef.current) {
      scriptNodeRef.current.disconnect();
      scriptNodeRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioCtxRef.current && audioCtxRef.current.state !== "closed") {
      audioCtxRef.current.close().catch(() => {});
      audioCtxRef.current = null;
    }
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ action: "stop" }));
        wsRef.current.close();
      }
      wsRef.current = null;
    }
    setStatus("stopped");
  }, []);

  useEffect(() => {
    return () => {
      stopCapture();
    };
  }, [stopCapture]);

  const [chunksSent, setChunksSent] = useState<number>(0);
  const [bytesSent, setBytesSent] = useState<number>(0);
  const chunksSentRef = useRef<number>(0);
  const bytesSentRef = useRef<number>(0);

  const startCapture = async () => {
    setErrorMessage(null);
    setSnapshotSuccessMsg(null);
    setStatus("requesting_permission");
    chunksSentRef.current = 0;
    bytesSentRef.current = 0;
    setChunksSent(0);
    setBytesSent(0);

    // 1. Check browser mediaDevices support
    if (typeof window === "undefined" || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setStatus("error");
      setErrorMessage("NO_MICROPHONE_DEVICE: Browser does not support mediaDevices/getUserMedia audio capture.");
      return;
    }

    try {
      // 2. Request microphone stream
      console.log("[LiveAudioCapture] Requesting microphone permission...");
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: false, // Keep raw noise profile for DSP analysis & DeepFilterNet
          autoGainControl: true,   // Enable AGC for reliable speech input level
        },
        video: false,
      });

      mediaStreamRef.current = stream;
      console.log("[LiveAudioCapture] Microphone permission granted.");

      // 3. Create & resume Web Audio Context
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const audioCtx = new AudioCtx();
      if (audioCtx.state === "suspended") {
        console.log("[LiveAudioCapture] Resuming suspended AudioContext...");
        await audioCtx.resume();
      }
      audioCtxRef.current = audioCtx;
      const detectedSR = audioCtx.sampleRate;
      setSampleRate(detectedSR);

      // 4. Connect WebSocket to live audio endpoint
      const wsUrl = getLiveWebSocketUrl();
      console.log(`[LiveAudioCapture] Opening WebSocket connection to: ${wsUrl}`);
      
      // Update UI status to CONNECTING before onopen
      setStatus("connecting");
      
      const ws = new WebSocket(wsUrl);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`[LiveAudioCapture] WebSocket connected (OPEN) to ${wsUrl}`);
        // Send initial setup frame
        ws.send(
          JSON.stringify({
            action: "start",
            sample_rate: detectedSR,
            channels: 1,
            dtype: "float32",
          })
        );
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "session_started" || data.type === "status") {
            if (data.session_id) setSessionId(data.session_id);
            if (data.status === "capturing" || data.type === "session_started") {
              setStatus("capturing");
              console.log(`[LiveAudioCapture] Live capture session active: ${data.session_id}`);
            }
          } else if (data.type === "telemetry") {
            const telemetry: LiveTelemetry = data;
            setLatestTelemetry(telemetry);
            if (onLiveTelemetryUpdate) {
              onLiveTelemetryUpdate(telemetry);
            }
          }
        } catch {}
      };

      ws.onerror = (errEvent) => {
        console.error(`[LiveAudioCapture] WebSocket error on ${wsUrl}:`, errEvent);
        setStatus("error");
        setErrorMessage(`WebSocket connection to live backend failed (${wsUrl}). Ensure FastAPI server is running on port 8000.`);
      };

      ws.onclose = (closeEvent) => {
        console.log(`[LiveAudioCapture] WebSocket closed (code: ${closeEvent.code}, reason: ${closeEvent.reason || "none"})`);
        setStatus((prev) => (prev === "capturing" || prev === "connecting" ? "stopped" : prev));
      };

      // 5. Connect Web Audio processing graph
      const source = audioCtx.createMediaStreamSource(stream);
      // ScriptProcessor buffer size: 2048 samples (~42ms @ 48kHz)
      const bufferSize = 2048;
      const scriptNode = audioCtx.createScriptProcessor(bufferSize, 1, 1);
      scriptNodeRef.current = scriptNode;

      scriptNode.onaudioprocess = (audioProcessingEvent) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
        const inputBuffer = audioProcessingEvent.inputBuffer;
        const channelData = inputBuffer.getChannelData(0); // Float32Array

        // Measure peak amplitude of current frame
        let peak = 0;
        for (let i = 0; i < channelData.length; i++) {
          const abs = Math.abs(channelData[i]);
          if (abs > peak) peak = abs;
        }

        // Apply clean digital gain boost if mic hardware output is quiet (< 0.15 peak)
        let outputArray = channelData;
        if (peak > 0.0001 && peak < 0.15) {
          const boost = Math.min(6.0, 0.5 / peak);
          outputArray = new Float32Array(channelData.length);
          for (let i = 0; i < channelData.length; i++) {
            outputArray[i] = Math.max(-1.0, Math.min(1.0, channelData[i] * boost));
          }
        }

        // Clone Float32Array buffer to ensure clean 1D array slice
        const pcmBuffer = new Float32Array(outputArray).buffer;
        wsRef.current.send(pcmBuffer);

        chunksSentRef.current += 1;
        bytesSentRef.current += pcmBuffer.byteLength;

        if (chunksSentRef.current % 50 === 0) {
          setChunksSent(chunksSentRef.current);
          setBytesSent(bytesSentRef.current);
        }
      };

      source.connect(scriptNode);

      // Connect scriptNode -> silentGain (gain=0) -> destination
      // Prevents audio output feedback to speakers while forcing Web Audio engine to process frames continuously
      const silentGain = audioCtx.createGain();
      silentGain.gain.value = 0;
      scriptNode.connect(silentGain);
      silentGain.connect(audioCtx.destination);
    } catch (err: unknown) {
      stopCapture();
      setStatus("error");
      if (err instanceof DOMException) {
        if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
          setErrorMessage("MICROPHONE_PERMISSION_DENIED: Microphone access was denied by the browser/user.");
          return;
        }
        if (err.name === "NotFoundError" || err.name === "DevicesNotFoundError") {
          setErrorMessage("NO_MICROPHONE_DEVICE: No audio input device (microphone) was found on your system.");
          return;
        }
      }
      setErrorMessage(err instanceof Error ? `MICROPHONE_ERROR [${err.name}]: ${err.message}` : "Failed to initialize microphone.");
    }
  };

  const handleAnalyzeSnapshot = async () => {
    if (!sessionId) return;
    setIsAnalyzingSnapshot(true);
    setErrorMessage(null);
    setSnapshotSuccessMsg(null);
    try {
      const res = await analyzeLiveSnapshot(sessionId, 5.0);
      setSnapshotSuccessMsg(`✓ Gemini AI analysis completed for live snapshot (${res.file_id})`);
      if (onSnapshotAnalysisComplete) {
        onSnapshotAnalysisComplete(res);
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Live snapshot analysis failed.");
    } finally {
      setIsAnalyzingSnapshot(false);
    }
  };

  const handleDenoiseSnapshot = async () => {
    if (!sessionId) return;
    setIsDenoisingSnapshot(true);
    setErrorMessage(null);
    setSnapshotSuccessMsg(null);
    try {
      const res = await denoiseLiveSnapshot(sessionId, 5.0);
      setSnapshotSuccessMsg(`✓ DeepFilterNet enhanced live rolling snapshot (${res.file_id})`);
      if (onSnapshotDenoiseComplete) {
        onSnapshotDenoiseComplete(res);
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Live snapshot denoising failed.");
    } finally {
      setIsDenoisingSnapshot(false);
    }
  };

  // Convert dB (-100 to 0) to percentage bar height (0% to 100%)
  const dbLevel = latestTelemetry?.db ?? -100;
  const levelPercent = Math.max(0, Math.min(100, ((dbLevel + 60) / 60) * 100));

  return (
    <div className="bg-panel border border-line rounded-md p-4 flex flex-col gap-4">
      {/* Mode Switcher Tabs */}
      <div className="flex items-center justify-between border-b border-line/60 pb-3">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-tertiary uppercase tracking-wider font-semibold">
            INPUT SOURCE:
          </span>
          <div className="inline-flex rounded-md p-0.5 bg-surface border border-line">
            <button
              onClick={() => onInputModeChange("file")}
              className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
                inputMode === "file"
                  ? "bg-cyan-600 text-white font-medium shadow-sm"
                  : "text-secondary hover:text-primary"
              }`}
            >
              UPLOAD FILE
            </button>
            <button
              onClick={() => onInputModeChange("live")}
              className={`px-3 py-1 text-xs font-mono rounded transition-colors ${
                inputMode === "live"
                  ? "bg-cyan-600 text-white font-medium shadow-sm"
                  : "text-secondary hover:text-primary"
              }`}
            >
              LIVE MICROPHONE
            </button>
          </div>
        </div>

        {/* Live Status Badge */}
        {inputMode === "live" && (
          <div className="flex items-center gap-2">
            {status === "capturing" && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-red-500/10 text-red-400 border border-red-500/20 animate-pulse">
                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                ● LIVE CAPTURE
              </span>
            )}
            {status === "connecting" && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 animate-pulse">
                CONNECTING...
              </span>
            )}
            {status === "requesting_permission" && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                REQUESTING PERMISSION...
              </span>
            )}
            {(status === "idle" || status === "stopped") && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20">
                ● OFFLINE
              </span>
            )}
            {status === "error" && (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium bg-red-500/10 text-red-400 border border-red-500/20">
                ERROR
              </span>
            )}
          </div>
        )}
      </div>

      {/* Live Mode Controls & Level Meter */}
      {inputMode === "live" && (
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
            {/* Control Buttons */}
            <div className="sm:col-span-7 flex flex-wrap items-center gap-2">
              {status !== "capturing" ? (
                <button
                  onClick={startCapture}
                  disabled={status === "requesting_permission"}
                  className="px-4 py-2 bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white font-mono text-xs font-semibold rounded transition-colors flex items-center gap-2 shadow"
                >
                  <span className="w-2 h-2 rounded-full bg-white animate-pulse"></span>
                  START LIVE CAPTURE
                </button>
              ) : (
                <button
                  onClick={stopCapture}
                  className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white font-mono text-xs font-semibold rounded transition-colors"
                >
                  STOP CAPTURE
                </button>
              )}

              {status === "capturing" && (
                <>
                  <button
                    onClick={handleAnalyzeSnapshot}
                    disabled={isAnalyzingSnapshot}
                    className="px-3 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-mono text-xs font-medium rounded transition-colors"
                  >
                    {isAnalyzingSnapshot ? "ANALYZING..." : "ANALYZE LIVE SNAPSHOT"}
                  </button>

                  <button
                    onClick={handleDenoiseSnapshot}
                    disabled={isDenoisingSnapshot}
                    className="px-3 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-mono text-xs font-medium rounded transition-colors"
                  >
                    {isDenoisingSnapshot ? "DENOISING..." : "DENOISE SNAPSHOT"}
                  </button>
                </>
              )}
            </div>

            {/* Live Audio Level dB Meter */}
            <div className="sm:col-span-5 flex flex-col gap-1 bg-surface/60 border border-line/40 rounded p-2.5">
              <div className="flex justify-between items-center text-[10px] font-mono text-tertiary uppercase">
                <span>INPUT LEVEL</span>
                <span className="text-cyan-300 font-semibold">{dbLevel.toFixed(1)} dB</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden relative">
                <div
                  className="h-full transition-all duration-75 rounded-full bg-gradient-to-r from-emerald-500 via-yellow-500 to-red-500"
                  style={{ width: `${levelPercent}%` }}
                />
              </div>
              <div className="flex justify-between items-center text-[9px] font-mono text-tertiary">
                <span>SR: {sampleRate.toLocaleString()} Hz</span>
                <span>Buffer: {latestTelemetry?.buffer_duration_sec ?? 0}s</span>
              </div>
            </div>
          </div>

          {/* Feedback messages */}
          {errorMessage && (
            <div className="p-3 bg-red-950/20 border border-red-500/30 rounded text-xs font-mono text-red-300">
              {errorMessage}
            </div>
          )}

          {snapshotSuccessMsg && (
            <div className="p-3 bg-emerald-950/20 border border-emerald-500/30 rounded text-xs font-mono text-emerald-300">
              {snapshotSuccessMsg}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
