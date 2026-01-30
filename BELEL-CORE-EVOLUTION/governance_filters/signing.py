from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def _canonical_bytes(payload: Dict[str, Any]) -> bytes:
    import json
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_request(payload: Dict[str, Any], private_key_pem: bytes) -> str:
    key = serialization.load_pem_private_key(private_key_pem, password=None)
    digest = hashlib.sha256(_canonical_bytes(payload)).digest()
    sig = key.sign(
        digest,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(sig).decode("utf-8")


def verify_request_signature(payload: Dict[str, Any], signature_b64: str, public_key_pem_path: Path) -> bool:
    public_key = serialization.load_pem_public_key(public_key_pem_path.read_bytes())
    digest = hashlib.sha256(_canonical_bytes(payload)).digest()
    sig = base64.b64decode(signature_b64.encode("utf-8"))
    try:
        public_key.verify(
            sig,
            digest,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
