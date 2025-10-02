import os, base64
from .canonical import canonical_json, sha256hex

# ENV:
#  - ED25519_PRIV_B64 : base64-encoded 32-byte private key (seed)
# If not set, signing is skipped gracefully.

def load_private_key():
    b64 = os.environ.get("ED25519_PRIV_B64", "").strip()
    if not b64:
        return None
    raw = base64.b64decode(b64)
    if len(raw) != 32:
        raise ValueError("ED25519_PRIV_B64 must be base64 of 32-byte seed")
    return raw

def sign_bundle(bundle: dict) -> dict:
    """
    Returns bundle with verifier_sig and pubkey if key present, else unchanged.
    """
    seed = load_private_key()
    if not seed:
        # no key in env; skip signing
        return bundle

    from nacl.signing import SigningKey
    sk = SigningKey(seed)
    pk = sk.verify_key
    message = canonical_json(bundle)
    sig = sk.sign(message).signature  # 64 bytes
    bundle["verifier_sig"] = {
        "alg": "Ed25519",
        "sig_b64": base64.b64encode(sig).decode("utf-8"),
        "pubkey_b64": base64.b64encode(bytes(pk)).decode("utf-8"),
        "msg_hash": "sha256:" + sha256hex(message)
    }
    return bundle
