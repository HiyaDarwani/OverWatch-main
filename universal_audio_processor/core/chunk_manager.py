import numpy as np


class ChunkManager:
	"""Convert variable-size audio input into fixed-size chunks."""

	def __init__(self, chunk_size=1024, sample_rate=16000):
		if chunk_size <= 0:
			raise ValueError("chunk_size must be positive")
		if sample_rate <= 0:
			raise ValueError("sample_rate must be positive")

		self.chunk_size = chunk_size
		self.sample_rate = sample_rate
		self.leftover = np.array([], dtype=np.float32)

	def process_stream(self, data):
		"""Buffer input and return complete fixed-size chunks."""
		data = np.asarray(data, dtype=np.float32).reshape(-1)
		if data.size == 0:
			return []

		combined = np.concatenate((self.leftover, data))
		num_chunks = len(combined) // self.chunk_size
		split_at = num_chunks * self.chunk_size

		chunks = [
			combined[start:start + self.chunk_size].copy()
			for start in range(0, split_at, self.chunk_size)
		]
		self.leftover = combined[split_at:].copy()
		return chunks

	def reset(self):
		"""Discard buffered samples."""
		self.leftover = np.array([], dtype=np.float32)
