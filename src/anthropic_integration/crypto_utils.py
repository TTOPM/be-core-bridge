"""
Cryptographic utilities with Ed25519 (PyNaCl) signing.
Falls back to demo signature if libs/keys absent.
"""
import os, json, time, hashlib
from typing import Tuple

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def json_sha256_hex(obj) -> str:
    b = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256_hex(b)

def ed25519_keys_available() -> bool:
    return os.path.exists(os.path.join(os.path.dirname(__file__), "..", "keys", "ed25519_secret.key"))

def ed25519_sign(data_hash: str) -> Tuple[str, str]:
    try:
        from nacl.signing import SigningKey
        keys_dir = os.path.join(os.path.dirname(__file__), "..", "keys")
        with open(os.path.join(keys_dir, "ed25519_secret.key"), "rb") as f:
            sk = SigningKey(f.read())
        sig = sk.sign(bytes.fromhex(data_hash)).signature.hex()
        pk = sk.verify_key.encode().hex()
        return sig, pk
    except Exception as e:
        # fallback
        return f"sig:{data_hash[:16]}:{int(time.time())}", "pk:demo"

def sign_proof_hash(data_hash: str) -> dict:
    if ed25519_keys_available():
        sig, pk = ed25519_sign(data_hash)
        return {"scheme": "ed25519", "signature": sig, "pubkey_hex": pk}
    else:
        return {"scheme": "demo", "signature": f"sig:{data_hash[:16]}:{int(time.time())}", "pubkey_hex": "demo"}
