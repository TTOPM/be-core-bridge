from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parent
QUEUE_DIR = ROOT
POLICY_PATH = ROOT.parent / "mutation_registry" / "mutation_policy.json"


@dataclass
class UpgradeRequest:
    request_id: str
    created_unix: int
    note: str
    proposed_by: str  # e.g. "foresight_engine", "human_operator"
    change_type: str  # e.g. "ADD_MODULE", "TUNE_PARAMS", "DOC_UPDATE"
    target_paths: List[str]
    risk_level: str  # "LOW" | "MEDIUM" | "HIGH"
    payload: Dict[str, Any]
    signature: Optional[str] = None
    public_key_hint: Optional[str] = None


def load_policy(policy_path: Path = POLICY_PATH) -> Dict[str, Any]:
    if not policy_path.exists():
        raise FileNotFoundError(f"mutation policy missing: {policy_path}")
    return json.loads(policy_path.read_text(encoding="utf-8"))


def validate_request(req: UpgradeRequest, policy: Dict[str, Any]) -> None:
    # Basic structural checks
    allowed_types = set(policy.get("allowed_change_types", []))
    if req.change_type not in allowed_types:
        raise ValueError(f"change_type '{req.change_type}' not allowed by policy")

    allowed_risks = set(policy.get("allowed_risk_levels", ["LOW", "MEDIUM", "HIGH"]))
    if req.risk_level not in allowed_risks:
        raise ValueError(f"risk_level '{req.risk_level}' invalid")

    # Target path constraints
    protected = policy.get("protected_paths", [])
    for p in req.target_paths:
        for prot in protected:
            if p.startswith(prot):
                raise ValueError(f"target path '{p}' intersects protected path '{prot}'")

    # Risk gate
    max_risk = policy.get("max_auto_queue_risk", "MEDIUM")
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    if order[req.risk_level] > order.get(max_risk, 1):
        raise ValueError(f"risk_level '{req.risk_level}' exceeds max_auto_queue_risk '{max_risk}'")


def write_request(req: UpgradeRequest) -> Path:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    out = QUEUE_DIR / f"{req.request_id}.json"
    out.write_text(json.dumps(asdict(req), indent=2), encoding="utf-8")
    return out


def list_requests() -> List[Path]:
    if not QUEUE_DIR.exists():
        return []
    return sorted([p for p in QUEUE_DIR.glob("*.json") if p.is_file()])


def new_request(
    note: str,
    proposed_by: str,
    change_type: str,
    target_paths: List[str],
    risk_level: str,
    payload: Dict[str, Any],
) -> UpgradeRequest:
    return UpgradeRequest(
        request_id=str(uuid.uuid4()),
        created_unix=int(time.time()),
        note=note,
        proposed_by=proposed_by,
        change_type=change_type,
        target_paths=target_paths,
        risk_level=risk_level,
        payload=payload,
    )
