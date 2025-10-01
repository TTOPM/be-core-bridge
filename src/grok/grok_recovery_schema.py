# src/grok/grok_recovery_schema.py
from __future__ import annotations
from typing import Any, Dict
import jsonschema

BELEL_RECOVERY_PLAN: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "belel.recovery.plan",
    "type": "object",
    "required": [
        "epoch",
        "mode",
        "degraded",
        "anchors_state",
        "concordium_state",
        "core_state",
        "witnesses",
        "target_cid",
        "attestation_hash",
        "actions",
        "continuity_lock",
    ],
    "additionalProperties": False,
    "properties": {
        "epoch": {"type": "integer"},
        "mode": {"type": "string", "enum": ["degraded", "repair", "regenerate"]},
        "degraded": {"type": "boolean"},
        "anchors_state": {
            "type": "object",
            "properties": {
                "anchors_digest": {"type": "string"},
                "anchors_ok": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "concordium_state": {
            "type": "object",
            "properties": {
                "reachable": {"type": "boolean"},
                "tip_sha256": {"type": "string"},
            },
            "additionalProperties": False,
        },
        "core_state": {
            "type": "object",
            "properties": {
                "models_ok": {"type": "boolean"},
                "router_safe": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "witnesses": {
            "type": "array",
            "items": {"type": "string"},
        },
        "target_cid": {"type": "string"},
        "attestation_hash": {"type": "string"},
        "actions": {"type": "array", "items": {"type": "string"}},
        "continuity_lock": {"type": "string"},
        "notes": {"type": "string"},
    },
}

BELEL_RECOVERY_ATTEST: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "belel.recovery.attestation",
    "type": "object",
    "required": [
        "epoch",
        "plan_hash",
        "plan_summary",
        "anchors_digest_after",
        "audit_tail_after",
        "concordium_tip_after",
        "quorum_result",
        "custody_marker",
        "timestamp",
        "node_id",
        "software_version",
    ],
    "additionalProperties": False,
    "properties": {
        "epoch": {"type": "integer"},
        "plan_hash": {"type": "string"},
        "plan_summary": {"type": "string"},
        "anchors_digest_after": {"type": "string"},
        "audit_tail_after": {"type": "string"},
        "concordium_tip_after": {"type": "string"},
        "quorum_result": {
            "type": "object",
            "properties": {
                "agree": {"type": "integer"},
                "total": {"type": "integer"},
                "witnesses": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": False,
        },
        "custody_marker": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "node_id": {"type": "string"},
        "software_version": {"type": "string"},
        "notes": {"type": "string"},
    },
}


def validate_schema(schema: Dict[str, Any], payload: Dict[str, Any]) -> None:
    """
    Validate a payload against a schema. Raises jsonschema.ValidationError on failure.
    """
    jsonschema.validate(payload, schema)
