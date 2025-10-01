from __future__ import annotations
import json, hashlib, time, pathlib
LEDGER = pathlib.Path(__file__).resolve().parent / "ledger.jsonl"
def append(entry: dict) -> dict:
    prev_hash = None
    if LEDGER.exists():
        *_, last = LEDGER.read_text().strip().splitlines()
        prev_hash = json.loads(last).get("rolling_hash")
    body = json.dumps(entry, separators=(",", ":"), ensure_ascii=False)
    rolling_hash = hashlib.sha256(((prev_hash or "") + body).encode()).hexdigest()
    record = {"entry": entry, "prev_hash": prev_hash, "rolling_hash": rolling_hash, "ts": time.time()}
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record
