# BELEL_SELF_TEACHING/quarantine.py
from __future__ import annotations
from pathlib import Path
import json
import gzip
from typing import Dict, Any

Q_DIR = Path("BELEL_SELF_TEACHING/quarantine")
PENDING = Q_DIR / "pending"
REVERIFY = Q_DIR / "reverify"
MANIFESTS = Q_DIR / "manifests"
for p in (PENDING, REVERIFY, MANIFESTS):
    p.mkdir(parents=True, exist_ok=True)

def _write_jsonl_gz(path: Path, record: Dict[str, Any]):
    with gzip.open(path, "at", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def quarantine_record(record: Dict[str, Any], reason: str, cycle_id: str, reverify: bool = False) -> str:
    bucket = REVERIFY if reverify else PENDING
    fn = f"quarantine_{cycle_id.replace(':','-')}.jsonl.gz"
    path = bucket / fn
    record = dict(record)
    record["quarantine_reason"] = reason
    record["quarantine_cycle_id"] = cycle_id
    _write_jsonl_gz(path, record)
    return str(path)
