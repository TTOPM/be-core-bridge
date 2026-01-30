"""
self_upgrade_queue/queue_processor.py

Processes self-upgrade requests under governance filters.

Behavior:
- scans queue directory for upgrade_request*.json
- runs governance gate (governance_filters/filters.py)
- writes a decision receipt JSON
- moves request + receipt into processed/approved or processed/rejected

Run:
  python BELEL-CORE-EVOLUTION/self_upgrade_queue/queue_processor.py --repo-root . --queue-dir BELEL-CORE-EVOLUTION/self_upgrade_queue
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from governance_filters.filters import evaluate_upgrade_request


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _is_request_file(p: Path) -> bool:
    if not p.is_file():
        return False
    name = p.name.lower()
    return name.startswith("upgrade_request") and name.endswith(".json")


def _write_receipt(out_dir: Path, request_file: Path, decision: Dict[str, Any]) -> Path:
    receipt = {
        "ts": _utc_stamp(),
        "request_file": str(request_file.name),
        "decision": decision,
    }
    out_path = out_dir / f"{request_file.stem}__receipt.json"
    out_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return out_path


def _move(src: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    shutil.move(str(src), str(dst))
    return dst


def main() -> None:
    ap = argparse.ArgumentParser(description="Process Belel self-upgrade queue")
    ap.add_argument("--repo-root", required=True, help="Repo root path (e.g., .)")
    ap.add_argument("--queue-dir", required=True, help="Queue dir path (self_upgrade_queue)")
    args = ap.parse_args()

    repo_root = Path(args.repo_root).resolve()
    queue_dir = Path(args.queue_dir).resolve()

    processed_dir = queue_dir / "processed"
    approved_dir = processed_dir / "approved"
    rejected_dir = processed_dir / "rejected"

    processed_dir.mkdir(parents=True, exist_ok=True)
    (processed_dir / ".gitkeep").write_text("", encoding="utf-8")

    req_files = sorted([p for p in queue_dir.iterdir() if _is_request_file(p)])

    if not req_files:
        print("[queue] no upgrade requests found")
        return

    for req in req_files:
        decision = evaluate_upgrade_request(repo_root=repo_root, request_path=req)

        target_dir = approved_dir if decision.get("approved") else rejected_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        # Write receipt next to the moved files in the target dir
        receipt_path = _write_receipt(target_dir, req, decision)

        moved_req = _move(req, target_dir)
        print(f"[queue] {moved_req.name} -> {'APPROVED' if decision.get('approved') else 'REJECTED'}")
        print(f"[queue] receipt -> {receipt_path.name}")


if __name__ == "__main__":
    main()
