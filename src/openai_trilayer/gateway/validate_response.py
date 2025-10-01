"""
Runtime validator: ensure each response record has (a) ACK tool evidence,
(b) attestation schema fields, and (c) adjudication block.
Hook into your API layer or worker.
"""
import json, sys

def validate(payload: dict) -> None:
    a = payload.get("attestation", {})
    c = payload.get("concordium_decision", {})
    missing = []
    for k in ("ack_mandate","anchors_match","model","continuity","truth_lock","prompt_sha256","output_sha256","timestamp"):
        if not a.get(k): missing.append(f"attestation.{k}")
    if "is_compliant" not in c: missing.append("concordium_decision.is_compliant")
    if missing:
        raise SystemExit("Validation failed: " + ", ".join(missing))

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    validate(data)
