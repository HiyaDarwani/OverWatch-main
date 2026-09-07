"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { ProcessingTelemetry, ProcessingLogEvent, PipelineStageInfo } from "@/lib/api";

export type StreamStatus = "idle" | "running" | "paused" | "stopped" | "complete" | "error";

export function useAudioStream(fileId?: string) {
  const [sessionStatus, setSessionStatus] = useState<StreamStatus>("idle");
  const [speed, setSpeed] = useState<number>(1.0);
  const [frameIndex, setFrameIndex] = useState<number>(0);
  const [totalFrames, setTotalFrames] = useState<number>(0);
  const [progress, setProgress] = useState<number>(0.0);
  const [playheadSec, setPlayheadSec] = useState<number>(0.0);
  const [duration, setDuration] = useState<number>(0.0);

  const [strategy, setStrategy] = useState<string>("WIENER_FILTER");
  const [noiseType, setNoiseType] = useState<string>("stationary");
  const [confidence, setConfidence] = useState<number>(0.88);

  const [liveSpectrum, setLiveSpectrum] = useState<{ frequency: number[]; magnitude_db: number[] } | null>(null);
  const [liveTelemetry, setLiveTelemetry] = useState<ProcessingTelemetry | null>(null);
  const [bufferPercent, setBufferPercent] = useState<number>(25);
  const [overBudget, setOverBudget] = useState<boolean>(false);

  const [pipelineStages, setPipelineStages] = useState<PipelineStageInfo[]>([]);
  const [logs, setLogs] = useState<ProcessingLogEvent[]>([]);

  const wsRef = useRef<WebSocket | null>(null);

  const connectWebSocket = useCallback(() => {
    if (!fileId) return;

    const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const wsProtocol = apiBase.startsWith("https") ? "wss:" : "ws:";
    const host = apiBase.replace(/^https?:\/\//, "").replace(/\/+$/, "");
    const wsUrl = `${wsProtocol}//${host}/api/audio/${encodeURIComponent(fileId)}/stream`;

    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === "init") {
          if (msg.status) setSessionStatus(msg.status);
          if (msg.total_frames) setTotalFrames(msg.total_frames);
          if (msg.duration) setDuration(msg.duration);
          if (msg.strategy) setStrategy(msg.strategy);
          if (msg.noise_type) setNoiseType(msg.noise_type);
          if (msg.confidence) setConfidence(msg.confidence);
          if (msg.speed) setSpeed(msg.speed);
        } else if (msg.type === "stream_start") {
          setSessionStatus("running");
          if (msg.total_frames) setTotalFrames(msg.total_frames);
          if (msg.duration) setDuration(msg.duration);
          if (msg.strategy) setStrategy(msg.strategy);
          if (msg.noise_type) setNoiseType(msg.noise_type);
          if (msg.confidence) setConfidence(msg.confidence);
          if (msg.speed) setSpeed(msg.speed);
        } else if (msg.type === "frame_update") {
          setFrameIndex(msg.frame_index);
          if (msg.total_frames) setTotalFrames(msg.total_frames);
          if (msg.progress !== undefined) setProgress(msg.progress);
          if (msg.playhead_sec !== undefined) setPlayheadSec(msg.playhead_sec);
          if (msg.spectrum) setLiveSpectrum(msg.spectrum);
          if (msg.telemetry) {
            setLiveTelemetry(msg.telemetry);
            setBufferPercent(msg.telemetry.buffer_percent || 25);
            setOverBudget(Boolean(msg.telemetry.over_budget));
          }
          if (msg.stages) setPipelineStages(msg.stages);
        } else if (msg.type === "status") {
          setSessionStatus(msg.status);
        } else if (msg.type === "reset") {
          setSessionStatus("idle");
          setFrameIndex(0);
          setProgress(0);
          setPlayheadSec(0);
          setLiveSpectrum(null);
          setBufferPercent(25);
          setOverBudget(false);
        } else if (msg.type === "log") {
          if (msg.log) {
            setLogs((prev) => [...prev, msg.log]);
          }
        } else if (msg.type === "stream_complete") {
          setSessionStatus("complete");
          setProgress(1.0);
          if (msg.stages) setPipelineStages(msg.stages);
          if (msg.log) setLogs((prev) => [...prev, msg.log]);
        }
      } catch (e) {
        console.error("WebSocket payload error:", e);
      }
    };

    ws.onerror = (err) => {
      console.warn("WebSocket stream connection error:", err);
    };

    ws.onclose = () => {
      wsRef.current = null;
    };
  }, [fileId]);

  useEffect(() => {
    if (fileId) {
      connectWebSocket();
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [fileId, connectWebSocket]);

  const sendAction = (action: string, payload: Record<string, any> = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action, ...payload }));
    } else {
      connectWebSocket();
      setTimeout(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ action, ...payload }));
        }
      }, 250);
    }
  };

  const startStream = (targetSpeed?: number) => {
    const s = targetSpeed ?? speed;
    setSpeed(s);
    setSessionStatus("running");
    sendAction("start", { speed: s });
  };

  const pauseStream = () => {
    setSessionStatus("paused");
    sendAction("pause");
  };

  const resumeStream = () => {
    setSessionStatus("running");
    sendAction("resume");
  };

  const stopStream = () => {
    setSessionStatus("stopped");
    sendAction("stop");
  };

  const resetStream = () => {
    setSessionStatus("idle");
    setFrameIndex(0);
    setProgress(0);
    setPlayheadSec(0);
    setLiveSpectrum(null);
    setOverBudget(false);
    setBufferPercent(25);
    setLogs([]);
    sendAction("reset");
  };

  const changeSpeed = (newSpeed: number) => {
    setSpeed(newSpeed);
    sendAction("set_speed", { speed: newSpeed });
  };

  return {
    sessionStatus,
    speed,
    frameIndex,
    totalFrames,
    progress,
    playheadSec,
    duration,
    strategy,
    noiseType,
    confidence,
    liveSpectrum,
    liveTelemetry,
    bufferPercent,
    overBudget,
    pipelineStages,
    logs,
    startStream,
    pauseStream,
    resumeStream,
    stopStream,
    resetStream,
    changeSpeed,
  };
}
