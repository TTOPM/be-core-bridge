from __future__ import annotations

import threading
from typing import Any

from fastapi import HTTPException

_lock = threading.Lock()
_editor = None


def _load_editor() -> Any:
    """
    Loads your BelelEditEngine exactly once.

    You MUST adjust the import path here to match your repo.

    Expected interface:
      editor.apply(edit_request_dict: dict) -> dict with keys:
        {
          "project_id": "...",
          "version_id": "...",
          "wav_path": "...",
          "mel_path": "...",
          "wav_sidecar": "...",
          "receipt": "...",
          "edit_id": "...",
          "edit_type": "...",
          "benchmark": {...},
          "meta": {...}
        }
    """
    try:
        # CHANGE THIS IMPORT to your actual location
        from belel_hyper_core.edit_engine import BelelEditEngine  # type: ignore
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"BelelEditEngine import failed. Fix edit_singleton.py import. Error: {e}",
        )

    try:
        return BelelEditEngine()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BelelEditEngine init failed: {e}")


def get_editor() -> Any:
    global _editor
    if _editor is not None:
        return _editor
    with _lock:
        if _editor is None:
            _editor = _load_editor()
    return _editor
