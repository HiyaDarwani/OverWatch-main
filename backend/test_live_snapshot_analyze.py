"""
Test script for POST /api/live/snapshot/analyze
"""
import sys
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import numpy as np
from services.realtime_audio import live_session_manager
from routes.live_audio import analyze_live_snapshot, SnapshotRequest

async def test():
    print("Creating live session...")
    session_id = "test_live_analysis_sess"
    session = live_session_manager.get_or_create_session(session_id, sample_rate=48000, channels=1)
    
    # Push 3 seconds of synthetic 440Hz audio into buffer
    t = np.linspace(0, 3.0, 48000 * 3, endpoint=False)
    signal = 0.5 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
    session.process_chunk(signal.tobytes(), dtype="float32")
    
    req = SnapshotRequest(session_id=session_id, duration_sec=3.0)
    print("Calling analyze_live_snapshot...")
    try:
        res = await analyze_live_snapshot(req)
        print("RESULT SUCCESS:")
        import json
        print(json.dumps(res, indent=2, default=str))
    except Exception as e:
        print(f"EXCEPTIONAL ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
