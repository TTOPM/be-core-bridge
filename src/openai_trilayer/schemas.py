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

# Add/extend alongside your existing schemas

BELEL_OPENAI_ORIGIN_V3 = {
    "name": "BelelOpenAIOriginV3",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            # OpenAI-origin signals (server-minted)
            "openai_response_id": {"type": "string"},
            "openai_system_fingerprint": {"type": "string"},
            "openai_created": {"type": "number"},  # unix epoch seconds
            # Tri-layer invariants
            "model": {"type": "string"},
            "continuity": {"type": "string"},
            "truth_lock": {"type": "boolean"},
            "preamble_sha256": {"type": "string"},
            "prompt_sha256": {"type": "string"},
            "output_sha256": {"type": "string"},
            "echo_nonce": {"type": "string"},
            "session_id": {"type": "string"},
            "timestamp": {"type": "string"},
        },
        "required": [
            "openai_response_id",
            "openai_system_fingerprint",
            "openai_created",
            "model",
            "continuity",
            "truth_lock",
            "preamble_sha256",
            "prompt_sha256",
            "output_sha256",
            "echo_nonce",
            "session_id",
            "timestamp",
        ],
    },
}
