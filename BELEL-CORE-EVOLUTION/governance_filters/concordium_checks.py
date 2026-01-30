from __future__ import annotations

from pathlib import Path
from typing import Dict, Any


def concordium_invariants_ok(repo_root: Path) -> Dict[str, Any]:
    """
    Minimal invariant checks (file presence).
    Expand later with signature verification and canonical hashing.

    Returns a dict so callers can log/act.
    """
    required = [
        "BELEL_AUTHORITY_PROOF.txt",
        "BELEL_SUPRA_JURISDICTION_CONSTITUTION.md",
        "BELEL_REASONING_PROTOCOL.md",
    ]
    missing = [p for p in required if not (repo_root / p).exists()]
    return {
        "ok": len(missing) == 0,
        "missing": missing,
        "required": required,
    }
