# src/grok/grok_integrity_beacon.py
from __future__ import annotations
import os
import time
import json
import hashlib
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import requests

LOG = logging.getLogger("grok.integrity_beacon")
LOG.setLevel(logging.INFO)

DEFAULT_BEACON_PATH = os.getenv("GROK_BEACON_PATH", os.path.expanduser("~/.grok/beacons.log"))
DEFAULT_BEACON_INTERVAL = int(os.getenv("GROK_BEACON_INTERVAL_SEC", "300"))  # 5 minutes

@dataclass
class Beacon:
    ts: int
    belel_cid: str
    anchors_digest: str
    concordium_tip: Optional[str]
    audit_tail: Optional[str]

    def to_json(self) -> str:
        return json.dumps(
            {
                "ts": self.ts,
                "belel_cid": self.belel_cid,
                "anchors_digest": self.anchors_digest,
                "concordium_tip": self.concordium_tip,
                "audit_tail": self.audit_tail,
            },
            separators=(",", ":"),
            sort_keys=True,
        )

    def sha256(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


class BeaconEmitter:
    def __init__(self, beacon_path: str = DEFAULT_BEACON_PATH):
        self.path = beacon_path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def emit(self, beacon: Beacon) -> None:
        """Append a beacon JSON to the beacon log and flush immediately."""
        LOG.info("Emitting beacon: %s", beacon.to_json())
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(beacon.to_json() + "\n")
            fh.flush()
            os.fsync(fh.fileno())


class QuorumVerifier:
    """
    Verifies witness quorum: requires >= threshold of witnesses to agree on
    (belel_cid, anchors_digest, audit_tail). Witness sources can be URLs or local file paths.
    """

    def __init__(self, witnesses: List[str], threshold_ratio: float = 0.66):
        self.witnesses = witnesses
        self.threshold_ratio = threshold_ratio

    def _fetch_witness(self, w: str) -> Optional[Dict[str, Any]]:
        """Fetch a witness JSON from URL or read from file. Silently return None on failure."""
        try:
            if w.startswith("http://") or w.startswith("https://"):
                resp = requests.get(w, timeout=8)
                resp.raise_for_status()
                return resp.json()
            else:
                with open(w, "r", encoding="utf-8") as fh:
                    return json.load(fh)
        except Exception as e:
            LOG.warning("Failed to fetch witness %s: %s", w, e)
            return None

    def verify(self) -> Dict[str, Any]:
        """
        Returns a result with:
         - agree: number of witnesses that agreed on the modal triple
         - total: total fetched
         - modal: the modal triple (belel_cid, anchors_digest, audit_tail)
         - details: per-witness hashes and status
        """
        records = []
        for w in self.witnesses:
            data = self._fetch_witness(w)
            if not data:
                records.append({"witness": w, "ok": False})
                continue
            # we expect witness JSON to contain keys: belel_cid, anchors_digest, audit_tail or attestation_hash
            triple = (
                data.get("belel_cid") or data.get("cid") or data.get("target_cid"),
                data.get("anchors_digest") or data.get("attestation_hash") or data.get("attestation"),
                data.get("audit_tail") or data.get("last_audit_hash"),
            )
            rec = {"witness": w, "ok": True, "triple": triple}
            records.append(rec)

        # compute modal triple (most common non-None triple)
        seen = {}
        for r in records:
            if not r.get("ok"):
                continue
            t = r["triple"]
            seen.setdefault(t, 0)
            seen[t] += 1
        if not seen:
            return {"agree": 0, "total": len(records), "modal": None, "details": records}

        modal, agree = max(seen.items(), key=lambda kv: kv[1])
        total = sum(1 for r in records if r.get("ok"))
        result = {
            "agree": agree,
            "total": total,
            "modal": modal,
            "details": records,
            "quorum": agree >= max(1, int(self.threshold_ratio * max(1, total))),
        }
        LOG.info("Quorum verify result: %s", result)
        return result
