import json, hashlib
def canonical_json(obj) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
def sha256hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()
