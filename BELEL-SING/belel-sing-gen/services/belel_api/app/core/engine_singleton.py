from __future__ import annotations

import threading
from typing import Any, Dict

from fastapi import HTTPException


_lock = threading.Lock()
_engine = None


def _load_engine() -> Any:
    """
    Loads your BelelHyperEngine exactly once.

    You MUST adjust the import path here to match your repo.

    Expected interface:
      engine.generate(
        prompt: str,
        lyrics: str,
        duration_sec: int,
        language: str,
        steps: int|None,
        guidance: float|None,
        seed: int|None,
        codec_ckpt: str|None,
        denoiser_ckpt: str|None,
        meta: dict|None
      ) -> dict with keys:
        {
          "wav_path": "...",
          "mel_path": "...",
          "wav_sidecar": "...",
          "meta": {...}
        }
    """
    try:
        # CHANGE THIS IMPORT to your actual location
        from belel_hyper_core.hyper_engine import BelelHyperEngine  # type: ignore
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"BelelHyperEngine import failed. Fix engine_singleton.py import. Error: {e}",
        )

    try:
        return BelelHyperEngine()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BelelHyperEngine init failed: {e}")


def get_engine() -> Any:
    global _engine
    if _engine is not None:
        return _engine
    with _lock:
        if _engine is None:
            _engine = _load_engine()
    return _engine
