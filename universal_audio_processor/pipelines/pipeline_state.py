from enum import Enum
import time


class PipelineState(Enum):
    INIT = "initializing"
    CALIBRATION = "calibrating"
    PROCESSING = "processing"
    ADAPTATION = "adapting"
    PAUSED = "paused"
    SHUTDOWN = "shutdown"
    ERROR = "error"


class StateMachine:
    """Small state machine for streaming pipeline lifecycle."""

    def __init__(self, calibration_duration=0.5, sample_rate=16000,
                 max_errors=5):
        if calibration_duration < 0 or sample_rate <= 0:
            raise ValueError("calibration_duration must be non-negative and sample_rate positive")
        self.state = PipelineState.INIT
        self.calibration_samples = int(calibration_duration * sample_rate)
        self.samples_processed = 0
        self.state_history = []
        self.error_count = 0
        self.max_errors = max_errors

    def transition_to(self, new_state):
        old_state = self.state
        self.state = new_state
        self.state_history.append({
            "from": old_state,
            "to": new_state,
            "timestamp": time.time(),
        })

    def update(self, chunk_size):
        if chunk_size < 0:
            raise ValueError("chunk_size must be non-negative")
        if self.state == PipelineState.INIT:
            self.transition_to(
                PipelineState.CALIBRATION if self.calibration_samples else PipelineState.PROCESSING
            )
        elif self.state == PipelineState.CALIBRATION:
            self.samples_processed += chunk_size
            if self.samples_processed >= self.calibration_samples:
                self.transition_to(PipelineState.PROCESSING)
        elif self.state == PipelineState.ADAPTATION:
            self.transition_to(PipelineState.PROCESSING)

    def handle_error(self, error):
        self.error_count += 1
        if self.error_count >= self.max_errors:
            self.transition_to(PipelineState.ERROR)
            raise RuntimeError("Too many pipeline errors") from error

    def is_calibrating(self):
        return self.state == PipelineState.CALIBRATION

    def is_processing(self):
        return self.state in (PipelineState.PROCESSING, PipelineState.ADAPTATION)

    def can_process(self):
        return self.is_processing()
