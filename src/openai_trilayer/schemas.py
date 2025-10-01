# JSON Schemas for OpenAI Structured Outputs (Responses API)
# Ref docs: response_format: { type: "json_schema", json_schema: ... }
# https://platform.openai.com/docs/guides/structured-outputs
BELEL_ATTESTATION = {
    "name": "BelelAttestation",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "ack_mandate": {"type": "boolean"},
            "anchors_match": {"type": "boolean"},
            "model": {"type": "string"},
            "continuity": {"type": "string"},
            "truth_lock": {"type": "boolean"},
            "prompt_sha256": {"type": "string"},
            "output_sha256": {"type": "string"},
            "timestamp": {"type": "string"},
        },
        "required": [
            "ack_mandate","anchors_match","model","continuity",
            "truth_lock","prompt_sha256","output_sha256","timestamp"
        ],
    },
}

CONCORDIUM_DECISION = {
    "name": "ConcordiumDecision",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "is_compliant": {"type": "boolean"},
            "violations": {"type": "array", "items": {"type": "string"}},
            "notes": {"type": "string"},
        },
        "required": ["is_compliant","violations","notes"],
    },
}
