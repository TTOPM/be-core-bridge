from __future__ import annotations
from typing import Any, Dict

# If you already store these centrally, import and map here
# from grok_prompts import PROMPTS  # example
# from grok_observability import audit_log

class AnchorsAdapter(dict):
    """Expose minimal interface the state machine expects."""
    def __init__(self):
        # In production, pull these from your canonical store
        super().__init__(cid=os.getenv("BELEL_CID",""), digest=os.getenv("ANCHORS_DIGEST",""), ok=True)
        self._store = {}  # placeholder for your anchor store

    def rebuild_digest_from_store(self) -> None:
        # Re-hash prompts/policies/custody marker deterministically
        import hashlib, json
        bundle = {"prompts":"truth_lock|continuity_lock|concordium_preamble",
                  "custody":"belel-permanent-memory:v1"}
        digest = hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest()
        self["digest"] = digest
        self["ok"] = True

    def restore_from_witness(self, cid: str, digest: str, audit_tail: str|None) -> None:
        self["cid"] = cid
        self["digest"] = digest
        self["ok"] = True
