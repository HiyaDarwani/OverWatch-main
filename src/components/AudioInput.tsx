"use client";

import { useEffect, useRef, useState } from "react";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { AudioFileMeta, AudioPlaybackStatus, SystemRunState } from "@/types/overwatch";
import {
  uploadAudio,
  getAudioUrl,
  getAudioAnalysis,
  analyzeAudioWithGemini,
  type AudioAnalysisResponse,
  type GeminiAnalysisData,
} from "@/lib/api";

interface AudioInputProps {
  file: AudioFileMeta | null;
  runState: SystemRunState;
  onFileUpload?: (meta: AudioFileMeta | null) => void;
  onAnalysisComplete?: (analysis: AudioAnalysisResponse) => void;
  onAnalysisStart?: () => void;
  onAnalysisError?: (errorMsg: string) => void;
  onGeminiStart?: () => void;
  onGeminiComplete?: (data: GeminiAnalysisData | null, errorMsg?: string | null) => void;
}

export type UploadState = "idle" | "uploading" | "analyzing" | "success" | "error";

function formatTime(sec: number) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function AudioInput({
  file,
  runState,
  onFileUpload,
  onAnalysisComplete,
  onAnalysisStart,
  onAnalysisError,
  onGeminiStart,
  onGeminiComplete,
}: AudioInputProps) {
  const [activeFile, setActiveFile] = useState<AudioFileMeta | null>(file);
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  const [playback, setPlayback] = useState<AudioPlaybackStatus>("ready");
  const [currentTime, setCurrentTime] = useState(0);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Sync activeFile if parent prop changes
  useEffect(() => {
    setActiveFile(file);
    if (!file) {
      setPlayback("ready");
      setCurrentTime(0);
    }
  }, [file]);

  const playing = playback === "playing";
  const hasAudioUrl = Boolean(activeFile?.audioUrl);

  const handleFileSelect = async (selectedFile: File) => {
    if (!selectedFile) return;

    // Purge old active file and parent state immediately on new upload
    setActiveFile(null);
    if (onFileUpload) {
      onFileUpload(null);
    }

    setUploadState("uploading");
    setUploadProgress(15);
    setErrorMessage("");

    // Reset current audio playback
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    setPlayback("ready");
    setCurrentTime(0);

    const progressInterval = setInterval(() => {
      setUploadProgress((p) => (p >= 85 ? p : p + 15));
    }, 150);

    try {
      const response = await uploadAudio(selectedFile);
      clearInterval(progressInterval);
      setUploadProgress(100);

      const audioUrl = getAudioUrl(response.file_id);
      const meta: AudioFileMeta = {
        fileId: response.file_id,
        filename: response.filename,
        durationSec: response.duration,
        sampleRateHz: response.sample_rate,
        channels: response.channels,
        format: response.format,
        audioUrl: audioUrl,
      };

      setActiveFile(meta);
      if (onFileUpload) {
        onFileUpload(meta);
      }

      // Transition to ANALYZING state for Phase 3 DSP
      setUploadState("analyzing");
      if (onAnalysisStart) onAnalysisStart();

      try {
        const analysisData = await getAudioAnalysis(response.file_id);
        setUploadState("success");
        if (onAnalysisComplete) {
          onAnalysisComplete(analysisData);
        }
      } catch (analysisErr: unknown) {
        setUploadState("error");
        const msg = analysisErr instanceof Error ? analysisErr.message : "Audio DSP analysis failed.";
        setErrorMessage(msg);
        if (onAnalysisError) onAnalysisError(msg);
      }
    } catch (err: unknown) {
      clearInterval(progressInterval);
      setUploadState("error");
      const msg = err instanceof Error ? err.message : "An unexpected error occurred during upload.";
      setErrorMessage(msg);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const togglePlayback = () => {
    if (hasAudioUrl && audioRef.current) {
      if (playing) {
        audioRef.current.pause();
        setPlayback("ready");
      } else {
        audioRef.current
          .play()
          .then(() => setPlayback("playing"))
          .catch((err) => {
            console.error("Playback failed:", err);
            setPlayback("error");
          });
      }
    } else {
      setPlayback((prev) => (prev === "playing" ? "ready" : "playing"));
    }
  };

  const duration = activeFile?.durationSec || 0;
  const progressPercent = duration > 0 ? Math.min(100, Math.max(0, (currentTime / duration) * 100)) : 0;

  return (
    <Panel>
      <PanelHeader
        title="Audio Input"
        eyebrow="01 · Source"
        right={
          <StatusBadge
            label={
              uploadState === "uploading"
                ? "Uploading"
                : uploadState === "analyzing"
                ? "Analyzing"
                : runState === "processing"
                ? "Streaming"
                : activeFile
                ? "Loaded"
                : "Standby"
            }
            tone={
              uploadState === "uploading" || uploadState === "analyzing" || runState === "processing"
                ? "cyan"
                : activeFile
                ? "green"
                : "neutral"
            }
            pulse={uploadState === "uploading" || uploadState === "analyzing" || runState === "processing"}
          />
        }
      />

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".wav,.mp3,.flac,audio/wav,audio/x-wav,audio/mpeg,audio/flac"
        onChange={handleFileInputChange}
        className="hidden"
      />

      {/* Hidden HTML5 Audio Element */}
      {hasAudioUrl && activeFile?.audioUrl && (
        <audio
          ref={audioRef}
          src={activeFile.audioUrl}
          onTimeUpdate={() => {
            if (audioRef.current) {
              setCurrentTime(audioRef.current.currentTime);
            }
          }}
          onEnded={() => {
            setPlayback("ready");
            setCurrentTime(0);
          }}
          onError={() => {
            setPlayback("error");
          }}
        />
      )}

      {/* Upload Dropzone / Status Box */}
      {uploadState === "idle" && (
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`border border-dashed rounded-sm px-4 py-5 flex flex-col items-center justify-center text-center gap-1.5 mb-4 transition-colors cursor-pointer group ${
            isDragging
              ? "border-cyan bg-cyan/10"
              : "border-line-active hover:border-cyan/50"
          }`}
        >
          <UploadIcon />
          <div className="text-[13px] text-secondary group-hover:text-primary transition-colors">
            Drop audio dataset here
          </div>
          <div className="text-[11px] text-tertiary font-data">
            or <span className="text-cyan underline underline-offset-2">Browse Files</span> (.wav primary)
          </div>
        </div>
      )}

      {uploadState === "uploading" && (
        <div className="border border-dashed border-cyan/60 bg-cyan/5 rounded-sm px-4 py-5 flex flex-col items-center justify-center text-center gap-2 mb-4">
          <SpinnerIcon />
          <div className="text-[12.5px] text-cyan font-data font-medium tracking-wide">
            UPLOADING... {uploadProgress}%
          </div>
          <div className="w-full max-w-[220px] h-1.5 bg-panel rounded-full overflow-hidden border border-line">
            <div
              className="h-full bg-cyan transition-all duration-200"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {uploadState === "analyzing" && (
        <div className="border border-dashed border-cyan/60 bg-cyan/5 rounded-sm px-4 py-5 flex flex-col items-center justify-center text-center gap-2 mb-4">
          <SpinnerIcon />
          <div className="text-[12.5px] text-cyan font-data font-medium tracking-wide animate-pulse">
            PROCESSING ANALYSIS &amp; GEMINI AI...
          </div>
          <div className="w-full max-w-[220px] h-1.5 bg-panel rounded-full overflow-hidden border border-line relative">
            <div className="h-full bg-cyan w-1/2 rounded-full animate-pulse transition-all duration-300" />
          </div>
          <div className="text-[11px] font-data text-tertiary">
            Extracting real DSP features &amp; Gemini 3.7 Flash AI reasoning
          </div>
        </div>
      )}

      {uploadState === "success" && (
        <div className="border border-green/30 bg-green/5 rounded-sm p-3 mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-[12px] font-data text-green">
            <CheckIcon />
            <span className="font-semibold tracking-wide">ANALYSIS COMPLETE ✓</span>
          </div>
          <button
            onClick={() => {
              setUploadState("idle");
              if (fileInputRef.current) {
                fileInputRef.current.value = "";
                fileInputRef.current.click();
              }
            }}
            className="text-[11px] font-data text-cyan hover:underline transition-all cursor-pointer"
          >
            Upload Another
          </button>
        </div>
      )}

      {uploadState === "error" && (
        <div className="border border-red-500/40 bg-red-500/10 rounded-sm p-3 mb-4 flex flex-col gap-1.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-[12px] font-data text-red-400">
              <ErrorIcon />
              <span className="font-semibold tracking-wide">PROCESSING FAILED</span>
            </div>
            <button
              onClick={() => {
                setUploadState("idle");
                if (fileInputRef.current) {
                  fileInputRef.current.value = "";
                  fileInputRef.current.click();
                }
              }}
              className="text-[11px] font-data text-cyan hover:underline cursor-pointer"
            >
              Try Again
            </button>
          </div>
          <div className="text-[11.5px] font-data text-tertiary">
            {errorMessage}
          </div>
        </div>
      )}

      {/* Audio Metadata Card & Player (Only rendered when activeFile is loaded!) */}
      {activeFile ? (
        <div className="bg-panel-inset border border-line rounded-sm p-3">
          <div className="flex items-center justify-between mb-2.5">
            <div className="flex items-center gap-2 min-w-0">
              <WaveIcon />
              <span className="font-data text-[12.5px] text-primary truncate" title={activeFile.filename}>
                {activeFile.filename}
              </span>
            </div>
            {activeFile.fileId && (
              <span className="font-data text-[10px] text-tertiary px-1.5 py-0.5 rounded border border-line bg-panel">
                ID: {activeFile.fileId}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 mb-3">
            <button
              onClick={togglePlayback}
              aria-label={playing ? "Pause" : "Play"}
              className="shrink-0 w-8 h-8 rounded-sm border border-line-active flex items-center justify-center text-primary hover:border-cyan hover:text-cyan transition-colors cursor-pointer"
            >
              {playing ? <PauseIcon /> : <PlayIcon />}
            </button>

            <div className="flex-1 min-w-0">
              <div className="h-1.5 bg-panel rounded-full overflow-hidden border border-line">
                <div
                  className="h-full bg-cyan transition-[width] duration-150"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <div className="flex justify-between mt-1.5 font-data text-[10.5px] text-tertiary">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-3 border-t border-line">
            <Stat label="Duration" value={`${duration.toFixed(1)} s`} />
            <Stat
              label="Sample Rate"
              value={`${(activeFile.sampleRateHz / 1000).toFixed(activeFile.sampleRateHz % 1000 === 0 ? 0 : 1)} kHz`}
            />
            <Stat
              label="Channels"
              value={`${activeFile.channels ?? 1} (${(activeFile.channels ?? 1) === 1 ? "Mono" : "Stereo"})`}
            />
            <Stat label="Format" value={(activeFile.format || "wav").toUpperCase()} />
          </div>
        </div>
      ) : (
        <div className="p-4 bg-panel-inset/50 border border-line/60 rounded-sm text-center font-data text-[12px] text-tertiary">
          No audio file selected. Upload a WAV file above to inspect real signal features.
        </div>
      )}
    </Panel>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] tracking-[0.1em] text-tertiary font-data uppercase mb-0.5">
        {label}
      </div>
      <div className="font-data text-[13px] text-primary font-medium">{value}</div>
    </div>
  );
}

function UploadIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className="text-tertiary">
      <path
        d="M12 16V4M12 4L7 9M12 4L17 9M5 20H19"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" className="animate-spin text-cyan">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="32" strokeDashoffset="10" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-green">
      <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-red-400">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
      <path d="M12 8v4m0 4h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function WaveIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-cyan shrink-0">
      <path
        d="M3 12h2l2-7 3 14 3-11 2 7 2-4h4"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PlayIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
      <path d="M6 4l14 8-14 8V4z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
      <rect x="5" y="4" width="5" height="16" />
      <rect x="14" y="4" width="5" height="16" />
    </svg>
  );
}
