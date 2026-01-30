from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Tuple

from self_upgrade_queue.queue import UpgradeRequest, load_policy, validate_request

# If you have a Concordium rules file, point to it here.
CONCORDIUM_RULES = Path(__file__).resolve().parent.parent.parent / "BELEL_REASONING_PROTOCOL.md"


@dataclass
class GovernanceDecision:
    approved: bool
    reason: str
    decision_notes: Dict[str, Any]


def _load_req(path: Path) -> UpgradeRequest:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return UpgradeRequest(**raw)


def review_request(req_path: Path) -> GovernanceDecision:
    policy = load_policy()
    req = _load_req(req_path)

    # 1) Policy validation (hard gate)
    try:
        validate_request(req, policy)
    except Exception as e:
        return GovernanceDecision(False, f"Policy gate failed: {e}", {"gate": "policy"})

    # 2) Concordium / constitutional sanity checks (hard gate)
    # (Here you enforce "no protected edits" already via policy; this layer can enforce semantics.)
    if "defeat_authorship" in json.dumps(req.payload).lower():
        return GovernanceDecision(False, "Payload contains authorship defeat intent.", {"gate": "concordium"})

    # 3) Risk gating and required detail
    if req.risk_level == "HIGH":
        return GovernanceDecision(False, "High risk requests require explicit human review.", {"gate": "risk"})

    # 4) Minimal completeness check
    if not req.note.strip():
        return GovernanceDecision(False, "Request note required.", {"gate": "completeness"})

    return GovernanceDecision(True, "Approved by governance filters.", {"gate": "approved"})
