from __future__ import annotations

from typing import Dict, Any, List

from self_upgrade_queue.queue import new_request, load_policy, validate_request, write_request


def propose_from_foresight(
    note: str,
    change_type: str,
    target_paths: List[str],
    risk_level: str,
    payload: Dict[str, Any],
):
    policy = load_policy()
    req = new_request(
        note=note,
        proposed_by="foresight_engine",
        change_type=change_type,
        target_paths=target_paths,
        risk_level=risk_level,
        payload=payload,
    )
    validate_request(req, policy)
    out = write_request(req)
    return out
