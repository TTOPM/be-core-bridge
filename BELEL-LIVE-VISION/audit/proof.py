import hashlib

def make_live_proof(desc: str) -> str:
    return hashlib.sha256(desc.encode("utf-8")).hexdigest()[:16]
