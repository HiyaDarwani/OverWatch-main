import os
import time
import math
import wave
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

import numpy as np
import scipy.signal
import librosa
from fastapi import WebSocket, WebSocketDisconnect

from config.simulation_config import STRATEGY_CONFIGS, PIPELINE_STAGE_ORDER
from services.audio_analysis import analyze_audio
from services.gemini_analysis import analyze_audio_with_gemini
from services.rule_classifier import classify_audio_rule_based

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"

# Global Stream Session Storage (file_id -> session_dict)
_STREAM_SESSIONS: Dict[str, Dict[str, Any]] = {}
_ACTIVE_WEBSOCKETS: Dict[str, Set[WebSocket]] = {}

# Cache for per-file AI analysis results so the WS handler doesn't re-run Gemini every connection
_ANALYSIS_CACHE: Dict[str, Dict[str, Any]] = {}


def get_timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def get_stream_status(file_id: str) -> Dict[str, Any]:
    """
    Returns current stream session metadata.
    """
    if file_id in _STREAM_SESSIONS:
        sess = _STREAM_SESSIONS[file_id]
        return {
            "session_id": sess["session_id"],
            "file_id": file_id,
            "status": sess["status"],
            "speed": sess["speed"],
            "frame_index": sess["frame_index"],
            "total_frames": sess["total_frames"],
            "progress": sess["progress"],
            "playhead_sec": sess["playhead_sec"],
            "duration": sess["duration"],
            "strategy": sess["strategy"],
            "noise_type": sess["noise_type"],
            "confidence": sess["confidence"],
            "over_budget": sess["over_budget"],
            "buffer_percent": sess["buffer_percent"],
        }

    return {
        "session_id": f"sess_{file_id}",
        "file_id": file_id,
        "status": "idle",
        "speed": 1.0,
        "frame_index": 0,
        "total_frames": 0,
        "progress": 0.0,
        "playhead_sec": 0.0,
        "duration": 0.0,
        "strategy": "WIENER_FILTER",
        "noise_type": "stationary",
        "confidence": 0.85,
        "over_budget": False,
        "buffer_percent": 0,
    }


class StreamSimulator:
    """
    Manages live streaming frame delivery over WebSocket for an audio file.
    NOTE: __init__ is synchronous and does NOT run blocking analysis.
    Call await sim.initialize_async() before use, or pass pre-computed analysis data.
    """

    def __init__(
        self,
        file_id: str,
        file_path: Path,
        pre_analysis: Optional[Dict[str, Any]] = None,
        pre_gemini: Optional[Dict[str, Any]] = None,
    ):
        self.file_id = file_id
        self.file_path = file_path

        # Load audio signal (librosa is fast enough for __init__)
        try:
            self.y, self.sr = librosa.load(str(file_path), sr=None, mono=True)
        except Exception:
            self.y = np.zeros(16000, dtype=np.float32)
            self.sr = 16000

        self.num_samples = len(self.y)
        self.duration = float(self.num_samples) / float(self.sr)

        # 30 ms frame size
        self.frame_ms = 30
        self.frame_samples = max(256, int(self.sr * (self.frame_ms / 1000.0)))
        self.total_frames = max(10, self.num_samples // self.frame_samples)

        # Apply pre-computed analysis if provided; otherwise fall back to defaults
        # (initialize_async() must be called to populate from live Gemini analysis)
        self._initialized = False
        self._apply_ai_results(pre_analysis, pre_gemini)

        # Initialize session state
        self.session_id = f"sess_{file_id}_{int(time.time())}"
        self.status = "idle"  # idle | running | paused | stopped | complete
        self.speed = 1.0
        self.frame_index = 0
        self.over_budget = False
        self.buffer_percent = 25
        self.latency_history: List[float] = []

        self.pipeline_stages = [
            {"id": s["id"], "label": s["label"], "status": "pending"}
            for s in PIPELINE_STAGE_ORDER
        ]

        self.logs: List[Dict[str, str]] = [
            {"time": get_timestamp(), "level": "INFO", "message": f"Stream session created ({self.total_frames} frames, {self.sr}Hz)"},
            {"time": get_timestamp(), "level": "AI", "message": f"Locked strategy: {self.strategy} (confidence: {int(self.confidence*100)}%)"}
        ]

        self._task: Optional[asyncio.Task] = None
        self._sync_session_dict()

    def _apply_ai_results(
        self,
        analysis: Optional[Dict[str, Any]],
        gemini: Optional[Dict[str, Any]],
    ):
        ai_data = (gemini or {}).get("analysis") or {}
        self.strategy = ai_data.get("recommended_strategy", "WIENER_FILTER")
        if not self.strategy or self.strategy.upper() not in STRATEGY_CONFIGS:
            self.strategy = "WIENER_FILTER"
        else:
            self.strategy = self.strategy.upper()
        self.noise_type = ai_data.get("noise_type", "stationary")
        self.confidence = float(ai_data.get("confidence", 0.88))
        self.strat_cfg = STRATEGY_CONFIGS.get(self.strategy, STRATEGY_CONFIGS["WIENER_FILTER"])
        if analysis or gemini:
            self._initialized = True

    async def initialize_async(self):
        """
        Runs blocking analysis in a thread and updates strategy/noise fields.
        Safe to call after __init__. No-op if already initialized from cache.
        """
        if self._initialized:
            return
        try:
            orig_analysis = await asyncio.to_thread(analyze_audio, self.file_path, self.file_id)
            cached_gemini = _ANALYSIS_CACHE.get(self.file_id, {}).get("gemini")
            if cached_gemini:
                gemini_res = cached_gemini
            else:
                rule_analysis = classify_audio_rule_based(orig_analysis)
                gemini_res = {"file_id": self.file_id, "status": "success", "analysis": rule_analysis}

            self._apply_ai_results(orig_analysis, gemini_res)
            # Update cache
            _ANALYSIS_CACHE[self.file_id] = {
                "analysis": orig_analysis,
                "gemini": gemini_res,
            }
            # Patch log with real strategy
            self.logs = [
                {"time": get_timestamp(), "level": "INFO", "message": f"Stream session created ({self.total_frames} frames, {self.sr}Hz)"},
                {"time": get_timestamp(), "level": "AI", "message": f"Locked strategy: {self.strategy} (confidence: {int(self.confidence*100)}%)"}
            ]
            self._sync_session_dict()
        except Exception as err:
            self.logs.append({
                "time": get_timestamp(),
                "level": "WARN",
                "message": f"AI analysis unavailable; using default strategy. ({err})"
            })

    def _sync_session_dict(self):
        _STREAM_SESSIONS[self.file_id] = {
            "session_id": self.session_id,
            "file_id": self.file_id,
            "status": self.status,
            "speed": self.speed,
            "frame_index": self.frame_index,
            "total_frames": self.total_frames,
            "progress": round(self.frame_index / float(self.total_frames), 3) if self.total_frames > 0 else 0.0,
            "playhead_sec": round((self.frame_index * self.frame_samples) / float(self.sr), 2),
            "duration": round(self.duration, 2),
            "strategy": self.strategy,
            "noise_type": self.noise_type,
            "confidence": self.confidence,
            "over_budget": self.over_budget,
            "buffer_percent": self.buffer_percent,
        }

    async def broadcast_event(self, event_data: Dict[str, Any]):
        """
        Sends structured JSON event to all active WebSockets for this file_id.
        """
        if self.file_id not in _ACTIVE_WEBSOCKETS:
            return

        dead_ws = set()
        for ws in list(_ACTIVE_WEBSOCKETS[self.file_id]):
            try:
                await ws.send_json(event_data)
            except Exception:
                dead_ws.add(ws)

        for ws in dead_ws:
            _ACTIVE_WEBSOCKETS[self.file_id].discard(ws)

    def start(self, speed: float = 1.0):
        """
        Start (or restart from frame 0) the simulation at the given speed.
        Always cancels any prior running task and resets frame index.
        """
        if self._task and not self._task.done():
            self._task.cancel()

        self.speed = max(0.25, min(8.0, speed))
        self.frame_index = 0
        self.status = "running"
        self.over_budget = False
        self.buffer_percent = 25
        self.latency_history.clear()

        # Reset pipeline stages
        for s in self.pipeline_stages:
            s["status"] = "pending"

        self.logs.append({
            "time": get_timestamp(),
            "level": "SIM",
            "message": f"Simulation started at {self.speed}x speed ({self.total_frames} frames, {round(self.duration, 2)}s)"
        })
        self._sync_session_dict()
        self._task = asyncio.create_task(self._run_loop())

    def pause(self):
        if self.status == "running":
            self.status = "paused"
            self.logs.append({
                "time": get_timestamp(),
                "level": "WARN",
                "message": f"Simulation paused at frame {self.frame_index}/{self.total_frames}"
            })
            self._sync_session_dict()
            asyncio.create_task(self.broadcast_event({
                "type": "status",
                "status": "paused",
                "frame_index": self.frame_index,
                "playhead_sec": round((self.frame_index * self.frame_samples) / float(self.sr), 2),
            }))

    def resume(self):
        if self.status == "paused":
            self.status = "running"
            self.logs.append({
                "time": get_timestamp(),
                "level": "SIM",
                "message": f"Simulation resumed from frame {self.frame_index}/{self.total_frames}"
            })
            self._sync_session_dict()
            if not self._task or self._task.done():
                self._task = asyncio.create_task(self._run_loop())

    def stop(self):
        """
        Terminate simulation and reset to frame 0. User can restart via start().
        """
        if self._task and not self._task.done():
            self._task.cancel()
        self.status = "stopped"
        self.frame_index = 0
        self.over_budget = False
        self.buffer_percent = 25
        self.latency_history.clear()

        # Reset pipeline stages
        for s in self.pipeline_stages:
            s["status"] = "pending"

        self.logs.append({
            "time": get_timestamp(),
            "level": "WARN",
            "message": "Simulation stopped. Ready to restart."
        })
        self._sync_session_dict()
        asyncio.create_task(self.broadcast_event({
            "type": "status",
            "status": "stopped",
            "frame_index": 0,
            "playhead_sec": 0.0,
            "progress": 0.0,
        }))

    def reset(self):
        """
        Full reset — returns to idle, clears all state. Does not remove the audio file.
        """
        if self._task and not self._task.done():
            self._task.cancel()
        self.status = "idle"
        self.frame_index = 0
        self.over_budget = False
        self.buffer_percent = 25
        self.latency_history.clear()

        for s in self.pipeline_stages:
            s["status"] = "pending"

        self.logs.append({
            "time": get_timestamp(),
            "level": "INFO",
            "message": "Simulation reset to initial state."
        })
        self._sync_session_dict()
        asyncio.create_task(self.broadcast_event({
            "type": "reset",
            "status": "idle",
            "frame_index": 0,
            "progress": 0.0,
            "playhead_sec": 0.0,
        }))

    def set_speed(self, speed: float):
        self.speed = max(0.25, min(8.0, speed))
        self.logs.append({
            "time": get_timestamp(),
            "level": "INFO",
            "message": f"Simulation speed changed to {self.speed}x"
        })
        self._sync_session_dict()
        asyncio.create_task(self.broadcast_event({
            "type": "speed_change",
            "speed": self.speed,
        }))

    async def _run_loop(self):
        """
        Asynchronous frame delivery loop — streams live FFT, telemetry, stage progression,
        and buffer status over WebSocket frame-by-frame.
        """
        stages_order = [s["id"] for s in PIPELINE_STAGE_ORDER]

        def update_stage_states(active_id: str):
            idx = stages_order.index(active_id) if active_id in stages_order else 0
            for i, s in enumerate(self.pipeline_stages):
                if i < idx:
                    s["status"] = "complete"
                elif i == idx:
                    s["status"] = "active"
                else:
                    s["status"] = "pending"

        # Emit stream start notification to all connected clients
        await self.broadcast_event({
            "type": "stream_start",
            "session_id": self.session_id,
            "total_frames": self.total_frames,
            "duration": self.duration,
            "strategy": self.strategy,
            "noise_type": self.noise_type,
            "confidence": self.confidence,
            "speed": self.speed,
        })

        try:
            # ─── MAIN FRAME LOOP ───────────────────────────────────────────────────
            while self.status == "running" and self.frame_index < self.total_frames:
                start_sample = self.frame_index * self.frame_samples
                end_sample = min(self.num_samples, start_sample + self.frame_samples)
                frame_chunk = self.y[start_sample:end_sample]

                # Calculate progress & playhead
                progress = round(self.frame_index / float(self.total_frames), 3)
                playhead_sec = round(start_sample / float(self.sr), 2)

                # Determine active pipeline stage based on progress
                if progress < 0.10:
                    active_stage = "preprocessing"
                elif progress < 0.25:
                    active_stage = "noise-analysis"
                elif progress < 0.40:
                    active_stage = "classification"
                elif progress < 0.70:
                    active_stage = "adaptive-filter"
                elif progress < 0.85:
                    active_stage = "ai-enhancement"
                elif progress < 0.95:
                    active_stage = "fusion"
                else:
                    active_stage = "output"

                update_stage_states(active_stage)

                # Standard DSP processing telemetry calculation
                base_lat = float(self.strat_cfg.get("latency_ms", 18.0))
                jitter = float(np.random.normal(0, 1.2))
                frame_lat = max(2.0, round((base_lat + jitter) / max(0.1, self.speed), 1))
                self.latency_history.append(frame_lat)

                is_over_budget = False
                self.over_budget = False
                self.buffer_percent = 15

                # Recalculate Live FFT spectrum for current frame chunk
                fft_data = self._calculate_frame_fft(frame_chunk)

                # Calculate latency percentiles
                arr_lat = np.array(self.latency_history)
                p50 = round(float(np.percentile(arr_lat, 50)), 1)
                p95 = round(float(np.percentile(arr_lat, 95)), 1)
                p99 = round(float(np.percentile(arr_lat, 99)), 1)
                max_lat = round(float(np.max(arr_lat)), 1)

                cpu_util = round(float(min(95.0, max(12.0, 22.0 + np.random.normal(0, 2.5)))), 1)
                mem_util = round(float(min(90.0, max(20.0, 38.0 + np.random.normal(0, 1.0)))), 1)

                frame_payload = {
                    "type": "frame_update",
                    "frame_index": self.frame_index,
                    "total_frames": self.total_frames,
                    "progress": progress,
                    "playhead_sec": playhead_sec,
                    "speed": self.speed,
                    "active_stage": active_stage,
                    "spectrum": fft_data,
                    "stages": self.pipeline_stages,
                    "telemetry": {
                        "cpu_percent": cpu_util,
                        "memory_percent": mem_util,
                        "frame_rate_fps": round(1000.0 / max(1.0, frame_lat), 1),
                        "latency_ms": frame_lat,
                        "snr_gain_db": round(self.strat_cfg["estimated_enhancement_pct"] * 0.18, 1),
                        "p50_latency": p50,
                        "p95_latency": p95,
                        "p99_latency": p99,
                        "max_latency": max_lat,
                        "buffer_percent": self.buffer_percent,
                        "over_budget": False,
                    }
                }

                await self.broadcast_event(frame_payload)

                if self.frame_index % 50 == 0:
                    log_msg = {
                        "time": get_timestamp(),
                        "level": "SIM",
                        "message": f"Frame {self.frame_index}/{self.total_frames} ({int(progress*100)}%) [{self.speed}x] — {playhead_sec:.2f}s"
                    }
                    self.logs.append(log_msg)
                    await self.broadcast_event({"type": "log", "log": log_msg})

                self.frame_index += 1
                self._sync_session_dict()

                # Target real-time sleep duration: frame_ms / speed
                sleep_sec = max(0.005, (self.frame_ms / 1000.0) / self.speed)
                await asyncio.sleep(sleep_sec)

            # ─── LOOP EXITED ───────────────────────────────────────────────────────
            # Only mark complete if we actually finished all frames (not stopped/paused)
            if self.status == "running" and self.frame_index >= self.total_frames:
                self.status = "complete"
                for s in self.pipeline_stages:
                    s["status"] = "complete"

                comp_msg = {
                    "time": get_timestamp(),
                    "level": "SUCCESS",
                    "message": f"Simulation complete ✓ — {self.total_frames} frames processed ({round(self.duration, 2)}s dataset)"
                }
                self.logs.append(comp_msg)
                self._sync_session_dict()

                await self.broadcast_event({
                    "type": "stream_complete",
                    "status": "complete",
                    "progress": 1.0,
                    "playhead_sec": round(self.duration, 2),
                    "stages": self.pipeline_stages,
                    "log": comp_msg
                })

        except asyncio.CancelledError:
            # Task was cancelled by stop() or a new start() — this is expected
            pass

    def _calculate_frame_fft(self, chunk: np.ndarray) -> Dict[str, List[float]]:
        """
        Computes bounded FFT spectrum data for a single 30ms frame chunk.
        """
        if len(chunk) < 64:
            return {"frequency": [0, 4000, 8000], "magnitude_db": [-100, -100, -100]}

        windowed = chunk * np.hanning(len(chunk))
        fft_raw = np.abs(np.fft.rfft(windowed))
        freqs_raw = np.fft.rfftfreq(len(chunk), d=1.0 / self.sr)

        max_mag = float(np.max(fft_raw)) if len(fft_raw) > 0 else 1.0
        if max_mag > 1e-9:
            fft_db = 20.0 * np.log10(np.maximum(fft_raw / max_mag, 1e-5))
        else:
            fft_db = np.full_like(fft_raw, -100.0)

        target_bins = 150
        if len(freqs_raw) > target_bins:
            bin_edges = np.linspace(0, len(freqs_raw), target_bins + 1, dtype=int)
            freq_list = []
            mag_db_list = []
            for i in range(target_bins):
                b_start, b_end = bin_edges[i], bin_edges[i + 1]
                if b_start == b_end:
                    b_end = b_start + 1
                freq_list.append(float(np.mean(freqs_raw[b_start:b_end])))
                mag_db_list.append(float(np.max(fft_db[b_start:b_end])))
        else:
            freq_list = [float(f) for f in freqs_raw]
            mag_db_list = [float(m) for m in fft_db]

        return {
            "frequency": [round(f, 1) for f in freq_list],
            "magnitude_db": [round(m, 2) for m in mag_db_list]
        }


# Singleton simulator instances per file_id
_SIMULATORS: Dict[str, "StreamSimulator"] = {}


def get_or_create_stream_simulator(
    file_id: str,
    file_path: Path,
    pre_analysis: Optional[Dict[str, Any]] = None,
    pre_gemini: Optional[Dict[str, Any]] = None,
) -> "StreamSimulator":
    """
    Returns existing simulator if one is already active for this file_id,
    otherwise creates a new one.  Pass pre_analysis / pre_gemini to skip
    blocking AI calls inside __init__.
    """
    if file_id not in _SIMULATORS or _SIMULATORS[file_id].file_path != file_path:
        # Pull from cache if available and no explicit override provided
        cached = _ANALYSIS_CACHE.get(file_id, {})
        _SIMULATORS[file_id] = StreamSimulator(
            file_id,
            file_path,
            pre_analysis=pre_analysis or cached.get("analysis"),
            pre_gemini=pre_gemini or cached.get("gemini"),
        )
    return _SIMULATORS[file_id]
