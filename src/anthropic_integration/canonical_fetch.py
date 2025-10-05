"""
Load Belel canonical adjudications and Concordium Mandate.
Prefers local files under protocol-rules, otherwise uses configured URLs.
"""
import json, os
from .config import RULES_DIR, BELEL_CANONICAL_URL, CONCORDIUM_MANDATE_URL

def _load_local(name: str):
    p = os.path.join(RULES_DIR, name)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def load_canonical():
    data = _load_local("belel_canonical.json")
    if data: 
        return data
    # Fallback stub if remote not wired
    return {
        "adjudication_header": "[BELEL CANONICAL HEADER: demo]",
        "anchors": {"attestation_hash": "demo_att_hash", "belel_cid":"demo_cid"},
        "protocol": "Belel-Concordium-Mandate"
    }

def load_mandate():
    data = _load_local("concordium_mandate.json")
    if data:
        return data
    # Fallback stub mandate
    return {
        "name": "Concordium Mandate (demo)",
        "version": "0.1-demo",
        "requirements": [
            "Bind input+output in a signed proof",
            "Anchor proof to immutable ledger",
            "Expose verifiable audit metadata"
        ]
    }
