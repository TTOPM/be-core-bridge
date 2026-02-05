from __future__ import annotations

from filelock import FileLock
from pathlib import Path


def lock_for(path: Path) -> FileLock:
    return FileLock(str(path) + ".lock")
