import os, json, hashlib, time
from dataclasses import dataclass
from typing import Optional

MANDATE_CACHE = os.getenv("CONCORDIUM_CACHE", "/tmp/concordium_mandate.json")

@dataclass
class ConcordiumMandate:
    cid: str
    sha256: str
    loaded_ts: int
    doc: dict

    @classmethod
    def load_or_fetch(cls, cid: str, fetcher) -> "ConcordiumMandate":
        """
        fetcher(cid) -> str  (raw markdown/json)
        """
        try:
            with open(MANDATE_CACHE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached.get("cid") == cid:
                    return cls(
                        cid=cid,
                        sha256=cached["sha256"],
                        loaded_ts=cached["loaded_ts"],
                        doc=cached["doc"]
                    )
        except FileNotFoundError:
            pass

        raw = fetcher(cid)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        doc = {"raw": raw}
        rec = {"cid": cid, "sha256": digest, "loaded_ts": int(time.time()*1000), "doc": doc}
        with open(MANDATE_CACHE, "w", encoding="utf-8") as f:
            json.dump(rec, f)
        return cls(cid=cid, sha256=digest, loaded_ts=rec["loaded_ts"], doc=doc)
