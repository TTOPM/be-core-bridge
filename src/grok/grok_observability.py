import hashlib, json, time, os
from typing import Dict, Any, Optional

AUDIT_PATH = os.getenv("GROK_AUDIT_PATH", "/tmp/grok_audit.log")

def _ts() -> int:
    return int(time.time() * 1000)

def _hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

_prev_hash: Optional[str] = None

def integrity_chain_append(event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    global _prev_hash
    record = {
        "ts": _ts(),
        "event": event,
        "payload": payload,
        "prev": _prev_hash
    }
    record["hash"] = _hash(record)
    _prev_hash = record["hash"]
    _write(record)
    return record

def audit_log(event: str, payload: Dict[str, Any]) -> None:
    integrity_chain_append(event, payload)

def _write(record: Dict[str, Any]) -> None:
    line = json.dumps(record, separators=(",",":"))
    with open(AUDIT_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
