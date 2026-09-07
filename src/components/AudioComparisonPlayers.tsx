"use client";

import { useEffect, useRef, useState } from "react";
import { Panel, PanelHeader } from "@/components/ui/Panel";
import { StatusBadge } from "@/components/ui/StatusBadge";

interface AudioComparisonPlayersProps {
  originalUrl: string;
  processedUrl: string;
  originalFilename: string;
  processedFilename: string;
  strategy: string;
  isReady: boolean;
}

function formatTime(sec: number) {
  if (!sec || isNaN(sec) || !isFinite(sec)) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function AudioComparisonPlayers({
  originalUrl,
  processedUrl,
  originalFilename,
  processedFilename,
  strategy,
  isReady,
}: AudioComparisonPlayersProps) {
  const [origPlaying, setOrigPlaying] = useState(false);
  const [procPlaying, setProcPlaying] = useState(false);
  const [isComparing, setIsComparing] = useState(false);

  const [origTime, setOrigTime] = useState(0);
  const [origDuration, setOrigDuration] = useState(0);
  const [origError, setOrigError] = useState<string | null>(null);

  const [procTime, setProcTime] = useState(0);
  const [procDuration, setProcDuration] = useState(0);
  const [procError, setProcError] = useState<string | null>(null);

  const origRef = useRef<HTMLAudioElement | null>(null);
  const procRef = useRef<HTMLAudioElement | null>(null);
  const comparisonTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync duration on URL change or when readyState >= 1
  useEffect(() => {
    setOrigError(null);
    setOrigTime(0);
    setOrigPlaying(false);
    if (origRef.current) {
      if (origRef.current.readyState >= 1) {
        setOrigDuration(origRef.current.duration);
      }
    }
  }, [originalUrl]);

  useEffect(() => {
    setProcError(null);
    setProcTime(0);
    setProcPlaying(false);
    if (procRef.current) {
      if (procRef.current.readyState >= 1) {
        setProcDuration(procRef.current.duration);
      }
    }
  }, [processedUrl]);

  // Clean up comparison timer on unmount
  useEffect(() => {
    return () => {
      if (comparisonTimeoutRef.current) {
        clearTimeout(comparisonTimeoutRef.current);
      }
    };
  }, []);

  const toggleOrig = () => {
    if (!origRef.current) return;
    setOrigError(null);

    if (origPlaying) {
      origRef.current.pause();
      setOrigPlaying(false);
    } else {
      if (procRef.current) {
        procRef.current.pause();
        setProcPlaying(false);
      }
      origRef.current
        .play()
        .then(() => setOrigPlaying(true))
        .catch((err: Error) => {
          console.error("Original audio playback failed:", err);
          setOrigError(`Playback error: ${err.message}`);
          setOrigPlaying(false);
        });
    }
  };

  const toggleProc = () => {
    if (!procRef.current || !isReady) return;
    setProcError(null);

    if (procPlaying) {
      procRef.current.pause();
      setProcPlaying(false);
    } else {
      if (origRef.current) {
        origRef.current.pause();
        setOrigPlaying(false);
      }
      procRef.current
        .play()
        .then(() => setProcPlaying(true))
        .catch((err: Error) => {
          console.error("Enhanced audio playback failed:", err);
          setProcError(`Playback error: ${err.message}`);
          setProcPlaying(false);
        });
    }
  };

  const playSequentialComparison = () => {
    if (!origRef.current || !procRef.current || !isReady) return;
    setIsComparing(true);
    setOrigError(null);
    setProcError(null);

    // Stop current playback
    origRef.current.pause();
    procRef.current.pause();
    origRef.current.currentTime = 0;
    procRef.current.currentTime = 0;

    const handleOrigEnd = () => {
      setOrigPlaying(false);
      origRef.current?.removeEventListener("ended", handleOrigEnd);

      // Short 0.5s transition pause, then play Enhanced Audio
      comparisonTimeoutRef.current = setTimeout(() => {
        if (procRef.current) {
          procRef.current.currentTime = 0;
          procRef.current
            .play()
            .then(() => setProcPlaying(true))
            .catch((err: Error) => {
              console.error("Sequential comparison enhanced playback failed:", err);
              setProcError(`Sequential playback failed: ${err.message}`);
              setIsComparing(false);
            });

          const handleProcEnd = () => {
            setProcPlaying(false);
            setIsComparing(false);
            procRef.current?.removeEventListener("ended", handleProcEnd);
          };
          procRef.current.addEventListener("ended", handleProcEnd);
        }
      }, 500);
    };

    origRef.current.addEventListener("ended", handleOrigEnd);
    origRef.current
      .play()
      .then(() => setOrigPlaying(true))
      .catch((err: Error) => {
        console.error("Sequential comparison original playback failed:", err);
        setOrigError(`Sequential playback failed: ${err.message}`);
        setIsComparing(false);
      });
  };

  const origPct = origDuration > 0 ? Math.min(100, (origTime / origDuration) * 100) : 0;
  const procPct = procDuration > 0 ? Math.min(100, (procTime / procDuration) * 100) : 0;

  return (
    <Panel>
      <PanelHeader
        title="Audio Enhancement Comparison"
        eyebrow="06 · Before / After Playback"
        right={
          isReady ? (
            <StatusBadge label="Simulated Output Ready ✓" tone="green" />
          ) : (
            <StatusBadge label="Processing Output..." tone="cyan" pulse />
          )
        }
      />

      {/* HTML5 Audio Elements with explicit preload, MIME type, and error diagnostics */}
      <audio
        ref={origRef}
        src={originalUrl}
        preload="auto"
        onLoadedMetadata={() => {
          if (origRef.current) {
            setOrigDuration(origRef.current.duration);
            setOrigError(null);
          }
        }}
        onTimeUpdate={() => {
          if (origRef.current) setOrigTime(origRef.current.currentTime);
        }}
        onEnded={() => setOrigPlaying(false)}
        onError={(e) => {
          const err = e.currentTarget.error;
          const msg = err ? `Audio Load Error (code ${err.code}: ${err.message || "Invalid source"})` : "Failed to load audio source.";
          console.error("Audio error [Original]:", msg, originalUrl);
          setOrigError(msg);
        }}
      />

      <audio
        ref={procRef}
        src={processedUrl}
        preload="auto"
        onLoadedMetadata={() => {
          if (procRef.current) {
            setProcDuration(procRef.current.duration);
            setProcError(null);
          }
        }}
        onTimeUpdate={() => {
          if (procRef.current) setProcTime(procRef.current.currentTime);
        }}
        onEnded={() => setProcPlaying(false)}
        onError={(e) => {
          const err = e.currentTarget.error;
          const msg = err ? `Audio Load Error (code ${err.code}: ${err.message || "Invalid source"})` : "Failed to load audio source.";
          console.error("Audio error [Enhanced]:", msg, processedUrl);
          setProcError(msg);
        }}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
        {/* Left: Original Audio Player */}
        <div className="bg-panel-inset border border-cyan/30 rounded-sm p-3 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="font-data text-[10px] text-cyan font-bold tracking-wide uppercase px-1.5 py-0.5 rounded border border-cyan/30 bg-cyan/10">
              BEFORE · ORIGINAL AUDIO
            </span>
            <span className="font-data text-[11px] text-tertiary truncate max-w-[160px]" title={originalFilename}>
              {originalFilename}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleOrig}
              aria-label={origPlaying ? "Pause Original Audio" : "Play Original Audio"}
              className="shrink-0 w-8 h-8 rounded-sm border border-cyan flex items-center justify-center text-cyan hover:bg-cyan/10 transition-colors cursor-pointer"
            >
              {origPlaying ? <PauseIcon /> : <PlayIcon />}
            </button>

            <div className="flex-1 min-w-0">
              <div className="h-1.5 bg-panel rounded-full overflow-hidden border border-line">
                <div className="h-full bg-cyan transition-[width] duration-150" style={{ width: `${origPct}%` }} />
              </div>
              <div className="flex justify-between mt-1 font-data text-[10px] text-tertiary">
                <span>{formatTime(origTime)}</span>
                <span>{formatTime(origDuration)}</span>
              </div>
            </div>
          </div>

          {origError && (
            <div className="mt-1 text-[10.5px] font-data text-red border border-red/30 bg-red/10 rounded p-1.5 leading-tight">
              {origError}
            </div>
          )}
        </div>

        {/* Right: Processed / Enhanced Audio Player */}
        <div
          className={`bg-panel-inset border rounded-sm p-3 flex flex-col gap-2 transition-all ${
            isReady ? "border-green/30" : "border-line opacity-60"
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="font-data text-[10px] text-green font-bold tracking-wide uppercase px-1.5 py-0.5 rounded border border-green/30 bg-green/10">
              AFTER · ENHANCED AUDIO
            </span>
            <span className="font-data text-[10px] text-cyan px-1.5 py-0.5 rounded border border-cyan/30 bg-cyan/10">
              {(strategy || "WIENER_FILTER").replace(/_/g, " ")}
            </span>
          </div>

          {isReady ? (
            <div className="flex items-center gap-3">
              <button
                onClick={toggleProc}
                aria-label={procPlaying ? "Pause Enhanced Audio" : "Play Enhanced Audio"}
                className="shrink-0 w-8 h-8 rounded-sm border border-green flex items-center justify-center text-green hover:bg-green/10 transition-colors cursor-pointer"
              >
                {procPlaying ? <PauseIcon /> : <PlayIcon />}
              </button>

              <div className="flex-1 min-w-0">
                <div className="h-1.5 bg-panel rounded-full overflow-hidden border border-line">
                  <div className="h-full bg-green transition-[width] duration-150" style={{ width: `${procPct}%` }} />
                </div>
                <div className="flex justify-between mt-1 font-data text-[10px] text-tertiary">
                  <span>{formatTime(procTime)}</span>
                  <span>{formatTime(procDuration)}</span>
                </div>
              </div>

              <a
                href={processedUrl}
                download={processedFilename}
                className="shrink-0 text-[10.5px] font-data text-cyan hover:underline px-2 py-1 border border-cyan/30 rounded bg-cyan/5 transition-colors"
              >
                WAV
              </a>
            </div>
          ) : (
            <div className="py-2 text-center font-data text-[11px] text-tertiary animate-pulse">
              Simulated output will appear here after processing completion.
            </div>
          )}

          {procError && (
            <div className="mt-1 text-[10.5px] font-data text-red border border-red/30 bg-red/10 rounded p-1.5 leading-tight">
              {procError}
            </div>
          )}
        </div>
      </div>

      {/* Sequential Playback Control */}
      {isReady && (
        <div className="pt-2 border-t border-line flex items-center justify-between">
          <span className="text-[10.5px] font-data text-tertiary">
            Sequential Audition Mode (Original → 0.5s transition → Enhanced)
          </span>
          <button
            onClick={playSequentialComparison}
            disabled={isComparing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm bg-cyan/10 border border-cyan text-cyan font-data text-[11.5px] font-semibold tracking-wide uppercase hover:bg-cyan/20 transition-colors disabled:opacity-50 cursor-pointer"
          >
            <PlayIcon /> {isComparing ? "PLAYING COMPARISON..." : "PLAY COMPARISON"}
          </button>
        </div>
      )}
    </Panel>
  );
}

function PlayIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
      <path d="M6 4l14 8-14 8V4z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor">
      <rect x="5" y="4" width="5" height="16" />
      <rect x="14" y="4" width="5" height="16" />
    </svg>
  );
}
