
"""
hotword_iface.py — abstraction for production hotword engines.

Implementations should subclass HotwordEngine and implement:
- load(model_path, sensitivity)
- start(callback)   # invoke callback() when hotword is detected
- stop()

We provide a Porcupine-compatible shim placeholder; supply your own model files.
"""

from typing import Callable, Optional

class HotwordEngine:
    def load(self, model_path: str, sensitivity: float = 0.5): ...
    def start(self, callback: Callable[[], None]): ...
    def stop(self): ...

class PorcupineShim(HotwordEngine):
    def __init__(self):
        self._running=False
        self._cb=None

    def load(self, model_path: str, sensitivity: float = 0.5):
        # TODO: integrate actual Porcupine/other engine here.
        self.model_path=model_path; self.sensitivity=sensitivity

    def start(self, callback: Callable[[], None]):
        self._cb = callback
        self._running=True
        print("[hotword] Shim started (replace with real engine).")

    def stop(self):
        self._running=False
        print("[hotword] Shim stopped.")
