from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from ..constants import LOG_DIR

JSON = Dict[str, Any]


def quantum_fingerprint(entity_data: JSON, log_path: Optional[str] = None) -> str:
    """
    ENTANGLEMENT-SHIELD Fingerprinting

    Creates a deterministic SHA-256 chain over canonicalized JSON.
    Appends to logs/quantum_identity_log.jsonl with an "Entangled Seal".
    """
    canonical = json.dumps(entity_data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    hash_chain = hashlib.sha256(canonical).hexdigest()

    os.makedirs(LOG_DIR, exist_ok=True)
    if log_path is None:
        log_path = os.path.join(LOG_DIR, "quantum_identity_log.jsonl")

    record = {
        "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "hash": hash_chain,
        "seal": "Entangled Seal",
        "entity": entity_data,
    }

    with open(log_path, "a", encoding="utf-8") as log:
        log.write(json.dumps(record, ensure_ascii=False) + "\n")

    return hash_chain