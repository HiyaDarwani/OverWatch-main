# pipelines/realtime_pipeline.py
from core.audio_buffer import AudioFrameBuffer, ChunkManager
from pipelines.hybrid_pipeline import HybridAudioPipeline
import numpy as np
import time
import logging

logger = logging.getLogger(__name__)

class RealtimeAudioPipeline:
    """Real-time audio processing pipeline"""
    
    def __init__(self, config, callback=None):
        """
        Args:
            config: Configuration dictionary
            callback: Optional callback function(enhanced_audio)
        """
        self.config = config
        self.callback = callback
        
        # Initialize core pipeline
        self.pipeline = HybridAudioPipeline(config)
        
        # Frame buffer
        self.frame_buffer = AudioFrameBuffer(
            frame_size=config.get('frame_size', 2048),
            hop_size=config.get('hop_size', 512)
        )
        
        # Chunk manager
        self.chunk_manager = ChunkManager(
            chunk_size=config.get('chunk_size', 1024),
            sample_rate=config.get('sample_rate', 16000)
        )
        
        # Performance metrics
        self.latency_samples = []
        self.frame_count = 0
        
    def process_chunk(self, audio_chunk):
        """
        Process incoming audio chunk
        
        Args:
            audio_chunk: numpy array (variable length)
        
        Returns:
            List of enhanced audio chunks
        """
        start_time = time.time()
        
        # Get fixed-size chunks
        chunks = self.chunk_manager.process_stream(audio_chunk)
        
        enhanced_chunks = []
        
        for chunk in chunks:
            # Get frames from chunk
            frames = self.frame_buffer.write(chunk)
            
            # Process each frame
            for frame in frames:
                enhanced_frame = self.pipeline.process_frame(frame)
                enhanced_chunks.append(enhanced_frame)
            
            self.frame_count += 1
        
        # Measure latency
        latency_ms = (time.time() - start_time) * 1000
        self.latency_samples.append(latency_ms)
        
        # Call callback if provided
        if self.callback and enhanced_chunks:
            combined = np.concatenate(enhanced_chunks)
            self.callback(combined)
        
        return enhanced_chunks
    
    def get_stats(self):
        """Get performance statistics"""
        if not self.latency_samples:
            return {}
        
        return {
            'avg_latency_ms': np.mean(self.latency_samples),
            'max_latency_ms': np.max(self.latency_samples),
            'min_latency_ms': np.min(self.latency_samples),
            'frames_processed': self.frame_count
        }
    
    def reset(self):
        """Reset pipeline"""
        self.pipeline.reset()
        self.frame_buffer.reset()
        self.chunk_manager.reset()
        self.latency_samples.clear()
        self.frame_count = 0