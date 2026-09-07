import time
from collections import defaultdict
from contextlib import contextmanager

import numpy as np


class LatencyProfiler:
    """Collect bounded timing samples for named processing stages."""

    def __init__(self, max_samples=1000):
        self.timings = defaultdict(list)
        self.max_samples = max_samples

    @contextmanager
    def measure(self, stage_name):
        start = time.perf_counter()
        try:
            yield
        finally:
            samples = self.timings[stage_name]
            samples.append((time.perf_counter() - start) * 1000)
            del samples[:-self.max_samples]

    def get_report(self):
        return {
            stage: {
                "mean_ms": float(np.mean(values)),
                "std_ms": float(np.std(values)),
                "min_ms": float(np.min(values)),
                "max_ms": float(np.max(values)),
                "p95_ms": float(np.percentile(values, 95)),
                "count": len(values),
            }
            for stage, values in self.timings.items() if values
        }
