# core/audio_buffer.py
import numpy as np
from collections import deque
import threading

from core.chunk_manager import ChunkManager

class RingBuffer:
    """Thread-safe ring buffer for audio streaming"""
    
    def __init__(self, max_size=10, dtype=np.float32):
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.Lock()
        self.dtype = dtype
        
    def write(self, data):
        """Write data to buffer"""
        with self.lock:
            self.buffer.append(np.array(data, dtype=self.dtype))
    
    def read(self):
        """Read data from buffer (FIFO)"""
        with self.lock:
            if len(self.buffer) > 0:
                return self.buffer.popleft()
            return None
    
    def peek(self):
        """Peek at first element without removing"""
        with self.lock:
            if len(self.buffer) > 0:
                return self.buffer[0]
            return None
    
    def clear(self):
        """Clear buffer"""
        with self.lock:
            self.buffer.clear()
    
    def size(self):
        """Get current buffer size"""
        with self.lock:
            return len(self.buffer)
    
    def is_empty(self):
        """Check if buffer is empty"""
        return self.size() == 0
    
    def is_full(self):
        """Check if buffer is full"""
        return self.size() == self.buffer.maxlen


class AudioFrameBuffer:
    """Buffer that maintains overlap for STFT processing"""
    
    def __init__(self, frame_size=2048, hop_size=512):
        self.frame_size = frame_size
        self.hop_size = hop_size
        self.overlap_size = frame_size - hop_size
        
        # Circular buffer
        self.buffer = np.zeros(frame_size * 2, dtype=np.float32)
        self.write_pos = 0
        self.frames_ready = False
    
    def write(self, data):
        """Write new data and return complete frames"""
        frames = []
        
        for sample in data:
            self.buffer[self.write_pos] = sample
            self.write_pos += 1
            
            # Check if we have a complete frame
            if self.write_pos >= self.frame_size:
                # Extract frame
                frame = self.buffer[:self.frame_size].copy()
                frames.append(frame)
                
                # Shift buffer (keep overlap)
                self.buffer[:self.overlap_size] = self.buffer[self.hop_size:self.frame_size]
                self.write_pos = self.overlap_size
        
        return frames
    
    def flush(self):
        """Flush remaining data as a frame (zero-padded if needed)"""
        if self.write_pos > 0:
            frame = self.buffer[:self.frame_size].copy()
            self.reset()
            return frame
        return None
    
    def reset(self):
        """Reset buffer"""
        self.buffer.fill(0)
        self.write_pos = 0

