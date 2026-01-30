# SELF UPGRADE QUEUE (BELEL-CORE-EVOLUTION)

This directory is Belel’s **upgrade intake organ**.

Upgrade requests enter here as structured JSON.  
Requests are **evaluated by governance filters** before acceptance.

## Intake File

- `upgrade_request.json` (single-request convention)
- or multiple requests named `upgrade_request__<timestamp>__<slug>.json`

## Governance Gate

Requests are adjudicated through:

- `BELEL-CORE-EVOLUTION/governance_filters/filters.py`
- `BELEL-CORE-EVOLUTION/governance_filters/concordium_checks.py`

## Processing

Run:

```bash
python BELEL-CORE-EVOLUTION/self_upgrade_queue/queue_processor.py \
  --repo-root . \
  --queue-dir BELEL-CORE-EVOLUTION/self_upgrade_queue
Approved requests are moved into:
	•	self_upgrade_queue/processed/approved/

Rejected requests are moved into:
	•	self_upgrade_queue/processed/rejected/

Every decision is logged as a JSON receipt alongside the original request.
---

## `BELEL-CORE-EVOLUTION/self_upgrade_queue/upgrade_request.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://ttopm.com/belel/upgrade_request.schema.json",
  "title": "Belel Self-Upgrade Request",
  "type": "object",
  "required": ["note", "requested_by", "scope", "change_type", "targets", "created_utc"],
  "properties": {
    "note": {
      "type": "string",
      "minLength": 10,
      "description": "Human-readable reason for the upgrade request."
    },
    "requested_by": {
      "type": "string",
      "description": "Requester identity (e.g., Pearce Robinson)."
    },
    "scope": {
      "type": "string",
      "enum": ["bounded", "expansive"],
      "description": "bounded = small controlled changes; expansive = larger architectural changes."
    },
    "change_type": {
      "type": "string",
      "enum": ["bugfix", "feature", "research", "governance", "security", "performance", "docs"],
      "description": "Category of requested change."
    },
    "targets": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "string",
        "description": "Repo paths/modules intended to be touched."
      }
    },
    "created_utc": {
      "type": "string",
      "description": "UTC timestamp like 2026-01-30T00:00:00Z"
    },
    "constraints": {
      "type": "object",
      "description": "Explicit constraints and invariants required for acceptance.",
      "additionalProperties": true
    },
    "references": {
      "type": "array",
      "description": "Optional supporting links, papers, issues, commits.",
      "items": { "type": "string" }
    }
  },
  "additionalProperties": false
}
