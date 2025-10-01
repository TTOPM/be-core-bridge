# attest/ledger_v2.py
"""
Append-only ledger with rolling hash.
Optionally anchors Merkle roots to external blockchains
via attest/blockchain_anchor.py.
"""

from __future__ import annotations
import json, hashlib, time, pathlib
from . import blockchain_anchor

LEDGER = pathlib.Path(__file__).resolve().parent / "ledger.jsonl"

def append(entry: dict, do_anchor: bool = False) -> dict:
    """
    Append an attestation entry to the ledger.
    Each record includes: entry, prev_hash, rolling_hash, timestamp.
    If do_anchor=True, compute Merkle root of all rolling_hashes and
    call blockchain_anchor.anchor(root) for external audit.
    """
    prev_hash = None
    if LEDGER.exists():
        *_, last = LEDGER.read_text().strip().splitlines()
        prev_hash = json.loads(last).get("rolling_hash")

    body = json.dumps(entry, separators=(",", ":"), ensure_ascii=False)
    rolling_hash = hashlib.sha256(((prev_hash or "") + body).encode()).hexdigest()
    record = {
        "entry": entry,
        "prev_hash": prev_hash,
        "rolling_hash": rolling_hash,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    if do_anchor:
        try:
            # Collect all rolling hashes in the ledger to compute Merkle root
            hashes = []
            with LEDGER.open("r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    if "rolling_hash" in data:
                        hashes.append(data["rolling_hash"])
            root = blockchain_anchor.merkle_root(hashes)
            blockchain_anchor.anchor(root)
            record["anchored_root"] = root
        except Exception as e:
            record["anchor_error"] = str(e)

    return record
