from datetime import datetime, timezone
from .canonical import canonical_json, sha256hex

def make_bundle(subject:str, kind:str, payload, sources:list, tools_used:list, version="1"):
    bundle = {
        "v": version,
        "continuity": "v4",
        "truth_lock": True,
        "subject": subject,
        "kind": kind,
        "payload": payload,
        "sources": sources,
        "tools_used": tools_used,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    cj = canonical_json(bundle)
    bundle["integrity_hash"] = "sha256:" + sha256hex(cj)
    return bundle
