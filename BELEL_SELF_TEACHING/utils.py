# BELEL_SELF_TEACHING/utils.py
import hashlib
import datetime

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def utc_cycle_id() -> str:
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
