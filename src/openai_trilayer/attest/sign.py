from __future__ import annotations
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import json, base64, pathlib

KEY_DIR = pathlib.Path(__file__).resolve().parent
PRIV = KEY_DIR / "private_key.pem"
PUB  = KEY_DIR / "public_key.pem"

def gen_keys():
    key = Ed25519PrivateKey.generate()
    PRIV.write_bytes(key.private_bytes(Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    PUB.write_bytes(key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))

def sign_json(obj: dict) -> str:
    key = serialization.load_pem_private_key(PRIV.read_bytes(), password=None)
    msg = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()
    sig = key.sign(msg)
    return base64.b64encode(sig).decode()
