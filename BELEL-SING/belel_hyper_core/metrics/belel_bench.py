from __future__ import annotations
import time
import torch

class BelelBench:
    def __init__(self):
        self.reset()

    def reset(self):
        self.t0 = None
        self.t1 = None
        self.peak_vram = None

    def start(self):
        self.reset()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
            torch.cuda.synchronize()
        self.t0 = time.perf_counter()

    def stop(self):
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            self.peak_vram = torch.cuda.max_memory_allocated() / (1024**3)
        self.t1 = time.perf_counter()

    @property
    def seconds(self) -> float:
        return 0.0 if (self.t0 is None or self.t1 is None) else (self.t1 - self.t0)

    def report(self) -> dict:
        return {
            "seconds": round(self.seconds, 4),
            "peak_vram_gb": None if self.peak_vram is None else round(self.peak_vram, 4),
        }
