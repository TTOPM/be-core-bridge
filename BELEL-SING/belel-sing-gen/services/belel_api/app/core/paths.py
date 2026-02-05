from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

from fastapi import HTTPException


def resolve_sandbox_root(out_dir: str) -> Path:
    root = Path(out_dir).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except Exception:
        return False


def resolve_under_root(root: Path, unsafe_path: str) -> Path:
    """
    Resolves a user-supplied path under the sandbox root.

    Accepts:
      - relative paths like outputs/... (we strip leading slashes)
      - paths already relative to root (recommended)
      - absolute paths ONLY if they still live under root

    Rejects:
      - any traversal outside root
    """
    if not unsafe_path:
        raise HTTPException(status_code=400, detail="path is required")

    # Normalize
    p = Path(unsafe_path)
    if str(p).startswith("file://"):
        p = Path(str(p).replace("file://", ""))

    if p.is_absolute():
        resolved = p.resolve()
    else:
        # remove leading ./ or /
        clean = str(p).lstrip("/").lstrip("\\")
        resolved = (root / clean).resolve()

    if not _is_within(resolved, root):
        raise HTTPException(status_code=403, detail="path escapes sandbox root")

    return resolved


def ensure_exists(p: Path) -> Path:
    if not p.exists():
        raise HTTPException(status_code=404, detail="artifact not found")
    return p


def guess_media_type(path: Path) -> str:
    s = path.name.lower()
    if s.endswith(".wav"):
        return "audio/wav"
    if s.endswith(".json"):
        return "application/json"
    if s.endswith(".txt"):
        return "text/plain"
    if s.endswith(".pt"):
        # never serve raw torch tensors to browser unless explicitly allowed
        return "application/octet-stream"
    return "application/octet-stream"
