from abc import ABC, abstractmethod

import numpy as np


class AudioIOInterface(ABC):
    """Common lifecycle and audio contract for hardware and file I/O."""

    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def write(self, audio):
        pass

    @abstractmethod
    def stop(self):
        pass


class FileIO(AudioIOInterface):
    """Chunked WAV input/output adapter."""

    def __init__(self, input_path=None, output_path=None, chunk_size=1024,
                 sample_rate=16000):
        self.input_path = input_path
        self.output_path = output_path
        self.chunk_size = chunk_size
        self.sample_rate = sample_rate
        self.audio_data = None
        self.position = 0
        self.output_buffer = []

    def start(self):
        if self.input_path:
            from utils.audio_io import load_audio
            self.audio_data, self.sample_rate = load_audio(
                self.input_path, sr=self.sample_rate
            )

    def read(self):
        if self.audio_data is None or self.position >= len(self.audio_data):
            return None
        end = min(self.position + self.chunk_size, len(self.audio_data))
        chunk = self.audio_data[self.position:end]
        self.position = end
        return chunk

    def write(self, audio):
        self.output_buffer.append(np.asarray(audio, dtype=np.float32).copy())

    def stop(self):
        if self.output_path and self.output_buffer:
            from utils.audio_io import save_audio
            save_audio(
                self.output_path,
                np.concatenate(self.output_buffer),
                self.sample_rate,
            )
        self.output_buffer.clear()


class MicrophoneIO(AudioIOInterface):
    """Sounddevice adapter; sounddevice is imported only when started."""

    def __init__(self, sample_rate=16000, chunk_size=1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.stream = None

    def start(self):
        import sounddevice as sd
        self.stream = sd.InputStream(
            samplerate=self.sample_rate, blocksize=self.chunk_size, channels=1
        )
        self.stream.start()

    def read(self):
        if self.stream is None:
            return None
        data, _ = self.stream.read(self.chunk_size)
        return data[:, 0].astype(np.float32)

    def write(self, audio):
        if self.stream is None:
            return
        self.stream.write(np.asarray(audio).reshape(-1, 1))

    def stop(self):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
