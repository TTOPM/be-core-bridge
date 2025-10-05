"""
Validate a proof against the Concordium Mandate requirements.
"""
from .canonical_fetch import load_mandate

def validate_proof(proof: dict) -> list:
    mandate = load_mandate()
    issues = []
    # Minimal checks (expand as needed)
    if "proof_hash" not in proof: issues.append("Missing proof_hash")
    if "signature" not in proof: issues.append("Missing signature")
    if "anchored" not in proof: issues.append("Missing anchoring info")
    return issues
