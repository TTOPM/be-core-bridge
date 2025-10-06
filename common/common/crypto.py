# src/common/crypto.py
from typing import Tuple
import base64, json, hashlib
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError

def _load_priv(priv_str: str) -> SigningKey:
    try:
        # allow base64 or hex
        raw = base64.b64decode(priv_str)
    except Exception:
        raw = bytes.fromhex(priv_str)
    return SigningKey(raw)

def _load_pub(pub_str: str) -> VerifyKey:
    try:
        raw = base64.b64decode(pub_str)
    except Exception:
        raw = bytes.fromhex(pub_str)
    return VerifyKey(raw)

def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sign_json(obj, private_key: str) -> Tuple[str, str]:
    """
    Returns (sig_base64, payload_sha256_hex).
    """
    payload = canonical_json(obj)
    sig = _load_priv(private_key).sign(payload).signature
    return base64.b64encode(sig).decode(), sha256_hex(payload)

def verify_json(obj, signature_b64: str, public_key: str) -> bool:
    payload = canonical_json(obj)
    sig = base64.b64decode(signature_b64)
    try:
        _load_pub(public_key).verify(payload, sig)
        return True
    except BadSignatureError:
        return False
