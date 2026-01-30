from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from .concordium_checks import concordium_invariants_ok


def evaluate_upgrade_request(repo_root: Path, request_path: Path) -> Dict[str, Any]:
    """
    Reads an upgrade request JSON and returns a governance decision payload.
    This is the gatekeeper you wire into self_upgrade_queue processing.
    """
    inv = concordium_invariants_ok(repo_root)

    try:
        payload = json.loads(request_path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"approved": False, "reason": "invalid_json", "error": str(e), "invariants": inv}

    if not inv["ok"]:
        return {"approved": False, "reason": "missing_concordium_files", "invariants": inv, "request": payload}

    # Basic structure check
    note = str(payload.get("note", "")).strip()
    if not note:
        return {"approved": False, "reason": "missing_note", "invariants": inv, "request": payload}

    # Approved for downstream review/merge
    return {"approved": True, "reason": "passes_minimum_gate", "invariants": inv, "request": payload}
