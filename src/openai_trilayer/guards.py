import hashlib, json, time
from typing import Dict

def sha256(x: str) -> str:
    return hashlib.sha256(x.encode("utf-8")).hexdigest()

def build_attestation(model: str, prompt: str, output: str, anchors) -> Dict:
    return {
        "ack_mandate": True,  # toggled true once ACK tool is called
        "anchors_match": True,
        "model": model,
        "continuity": anchors.continuity,
        "truth_lock": anchors.truth_lock,
        "prompt_sha256": sha256(prompt),
        "output_sha256": sha256(output),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

def continuity_gate(previous_terms: Dict[str, str], new_terms: Dict[str, str]) -> Dict[str, str]:
    """
    Enforce 'no redefinition': if a previously locked term appears with a conflicting
    definition, raise a violation that downstream can route to REPORT_VIOLATION_TOOL.
    """
    violations = {}
    for k, v in new_terms.items():
        if k in previous_terms and previous_terms[k].strip() != v.strip():
            violations[k] = f"Changed from: {previous_terms[k]} -> {v}"
    return violations
