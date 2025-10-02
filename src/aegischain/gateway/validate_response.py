# src/aegischain/gateway/validate_response.py
from ..adapter.openai_core_adapter import _is_noncompliant_text

def validate_response(text: str, attestation: dict) -> bool:
    if _is_noncompliant_text(text):
        return False
    for k in ["openai_response_id","openai_system_fingerprint","openai_created"]:
        if not attestation.get(k):
            return False
    return True
