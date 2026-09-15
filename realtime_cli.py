#!/usr/bin/env python3
"""
OverWatch Real-Time CLI — Single-command real-time audio processing.

Usage:
    python realtime_cli.py [--model deepfilternet|fullsubnet] [--sr 16000|48000] [--chunk 1024]

This runs the entire OverWatch pipeline locally:
- Captures microphone input in real-time
- Processes through DSP + ML enhancement pipeline
- Outputs enhanced audio to speakers AND prints live analysis
"""

import sys
import os
import argparse
import threading
import time
import signal
import numpy as np
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import sounddevice as sd
except ImportError:
    print("❌ sounddevice not installed. Run: pip install sounddevice")
    sys.exit(1)

from universal_audio_processor.config import DEFAULT_CONFIG
from universal_audio_processor.pipelines.realtime_pipeline import RealtimeAudioPipeline
from universal_audio_processor.utils.platform_detector import PlatformDetector
from universal_audio_processor.utils.latency_profiler import LatencyProfiler


class RealTimeOverWatch:
    """Single-command real-time OverWatch processor."""

    def __init__(self, args):
        self.args = args
        self.running = False
        self.audio_queue = []
        self.queue_lock = threading.Lock()

        # Detect platform and get optimal config
        platform_info = PlatformDetector.detect()
        print(f"🖥️  Platform: {platform_info['platform']} | CPU: {platform_info['cpu_cores']} cores")
        if platform_info.get('gpu_available'):
            print(f"🚀 GPU: {platform_info['gpu_type']} available")

        optimal_config = PlatformDetector.get_optimal_config(platform_info)
        self.config = DEFAULT_CONFIG.copy()
        self.config.update(optimal_config)

        # Override with CLI args
        self.config['sample_rate'] = args.sr
        self.config['chunk_size'] = args.chunk
        self.config['frame_size'] = args.chunk * 2
        self.config['hop_size'] = args.chunk

        # Model selection
        if args.model == 'deepfilternet':
            self.config['use_ml'] = True
            self.config['model_path'] = 'models/deepfilternet.onnx'
            self.config['model_type'] = 'onnx'
            print("🤖 Model: DeepFilterNet3 (48kHz)")
        elif args.model == 'fullsubnet':
            self.config['use_ml'] = True
            self.config['model_path'] = 'models/fullsubnet.onnx'
            self.config['model_type'] = 'onnx'
            print("🤖 Model: FullSubNet+ (16kHz)")
        else:
            self.config['use_ml'] = False
            print("⚡ Mode: Classical DSP only (Wiener Filter + Spectral Subtraction)")

        self.config['spectral_method'] = args.method

        # Latency profiler
        self.profiler = LatencyProfiler()

        # Statistics
        self.chunks_processed = 0
        self.start_time = None

    def audio_callback(self, indata, outdata, frames, time_info, status):
        """Sounddevice callback - runs on audio thread."""
        if status:
            print(f"⚠️  Audio status: {status}", file=sys.stderr)

        # Input is mono, shape (frames, 1)
        input_chunk = indata[:, 0].copy().astype(np.float32)

        # Process through pipeline
        with self.profiler.profile('pipeline'):
            enhanced_chunks = self.pipeline.process_chunk(input_chunk)

        # Combine enhanced chunks for output
        if enhanced_chunks:
            enhanced_audio = np.concatenate(enhanced_chunks)
            # Ensure correct length for output
            if len(enhanced_audio) >= frames:
                outdata[:, 0] = enhanced_audio[:frames]
            else:
                outdata[:, 0] = np.pad(enhanced_audio, (0, frames - len(enhanced_audio)))
        else:
            outdata.fill(0)

        # Update stats
        self.chunks_processed += 1

        # Print live telemetry every ~50 chunks (~1 sec at 1024/16000)
        if self.chunks_processed % 50 == 0:
            self.print_telemetry()

    def print_telemetry(self):
        """Print live processing telemetry."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        stats = self.pipeline.get_stats()
        profiler_stats = self.profiler.get_stats()

        avg_latency = stats.get('avg_latency_ms', 0)
        max_latency = stats.get('max_latency_ms', 0)

        print(f"\r📊 Chunks: {self.chunks_processed} | "
              f"Time: {elapsed:.1f}s | "
              f"Avg Latency: {avg_latency:.2f}ms | "
              f"Max: {max_latency:.2f}ms | "
              f"Pipeline: {profiler_stats.get('pipeline', {}).get('avg_ms', 0):.2f}ms",
              end='', flush=True)

    def run(self):
        """Start the real-time processing loop."""
        print("\n" + "=" * 60)
        print("  OVERWATCH REAL-TIME AUDIO PROCESSOR")
        print("=" * 60)
        print(f"Sample Rate: {self.config['sample_rate']} Hz")
        print(f"Chunk Size:  {self.config['chunk_size']} samples ({self.config['chunk_size']/self.config['sample_rate']*1000:.1f} ms)")
        print(f"Frame Size:  {self.config['frame_size']} samples")
        print(f"Hop Size:    {self.config['hop_size']} samples")
        print(f"Method:      {self.config['spectral_method']}")
        print(f"ML Enabled:  {self.config['use_ml']}")
        if self.config['use_ml']:
            print(f"Model:       {self.config['model_path']} ({self.config['model_type']})")
        print("-" * 60)
        print("🎙️  Speak into your microphone...")
        print("🔊 Enhanced audio plays through speakers")
        print("📈 Live telemetry prints above")
        print("⏹️  Press Ctrl+C to stop")
        print("=" * 60 + "\n")

        # Initialize pipeline
        self.pipeline = RealtimeAudioPipeline(self.config)

        # Audio stream configuration
        stream_config = {
            'samplerate': self.config['sample_rate'],
            'blocksize': self.config['chunk_size'],
            'channels': 1,
            'dtype': 'float32',
            'callback': self.audio_callback,
        }

        self.running = True
        self.start_time = time.time()

        try:
            with sd.Stream(**stream_config):
                print("▶️  Stream started. Processing...")
                while self.running:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping...")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean shutdown."""
        self.running = False

        # Final stats
        elapsed = time.time() - self.start_time if self.start_time else 0
        stats = self.pipeline.get_stats()
        profiler_stats = self.profiler.get_stats()

        print("\n" + "=" * 60)
        print("  SESSION SUMMARY")
        print("=" * 60)
        print(f"Duration:       {elapsed:.1f} seconds")
        print(f"Chunks Processed: {self.chunks_processed}")
        print(f"Avg Latency:    {stats.get('avg_latency_ms', 0):.2f} ms")
        print(f"Max Latency:    {stats.get('max_latency_ms', 0):.2f} ms")
        print(f"Frames Processed: {stats.get('frames_processed', 0)}")
        print("-" * 60)
        print("Stage Latencies (avg):")
        for stage, data in profiler_stats.items():
            print(f"  {stage:20s}: {data.get('avg_ms', 0):.3f} ms")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="OverWatch Real-Time Audio Processor - Single command, live mic I/O",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Classical DSP only (Wiener filter)
  python realtime_cli.py

  # With DeepFilterNet3 (requires model download)
  python realtime_cli.py --model deepfilternet --sr 48000

  # With FullSubNet+ (16kHz)
  python realtime_cli.py --model fullsubnet --sr 16000

  # Spectral subtraction method
  python realtime_cli.py --method spectral_sub
        """
    )

    parser.add_argument(
        '--model',
        choices=['none', 'deepfilternet', 'fullsubnet'],
        default='none',
        help='Enhancement model to use (default: none - classical DSP only)'
    )
    parser.add_argument(
        '--sr', '--sample-rate',
        type=int,
        choices=[16000, 48000],
        default=16000,
        help='Sample rate in Hz (default: 16000)'
    )
    parser.add_argument(
        '--chunk', '--chunk-size',
        type=int,
        default=1024,
        help='Audio chunk size in samples (default: 1024)'
    )
    parser.add_argument(
        '--method',
        choices=['wiener', 'spectral_sub', 'mmse'],
        default='wiener',
        help='Classical DSP method (default: wiener)'
    )
    parser.add_argument(
        '--list-devices',
        action='store_true',
        help='List available audio devices and exit'
    )

    args = parser.parse_args()

    if args.list_devices:
        print("Available audio devices:")
        print(sd.query_devices())
        return

    # Check model files exist if ML enabled
    if args.model != 'none':
        model_path = Path(f"models/{args.model}.onnx")
        if not model_path.exists():
            print(f"⚠️  Model not found: {model_path}")
            print("   Run the setup scripts in backend/ to download models:")
            print("   powershell -ExecutionPolicy Bypass -File backend/setup_deepfilter.ps1")
            print("   powershell -ExecutionPolicy Bypass -File backend/setup_fullsubnet.ps1")
            print("   Or use --model none for classical DSP only")
            return

    app = RealTimeOverWatch(args)
    app.run()


if __name__ == "__main__":
    main()