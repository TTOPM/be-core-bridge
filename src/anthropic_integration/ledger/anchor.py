"""
Anchoring providers. Local ledger + hook for TSA/blockchain.
"""
import json, os, time
from ..config import LEDGER_PATH, ANCHOR_PROVIDER_URL

def append_local_ledger(record: dict):
    os.makedirs(os.path.dirname(LEDGER_PATH), exist_ok=True)
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, separators=(",", ":")) + "\n")

def anchor_to_blockchain(proof_hash: str) -> dict:
    # Stub: in production, POST proof_hash to a TSA/blockchain anchoring service
    return {
        "provider": ANCHOR_PROVIDER_URL or "local-stub",
        "status": "queued",
        "txid": f"stub-{int(time.time())}",
        "hash": proof_hash
    }
