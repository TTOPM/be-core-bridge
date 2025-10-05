"""
Validate objects against JSON Schema (runtime-optional).
Fallback: structural checks if jsonschema not available.
"""
import json, os
from .config import SCHEMAS_DIR

def validate_proof_record(obj: dict) -> list:
    schema_path = os.path.join(SCHEMAS_DIR, "proof_record.schema.json")
    issues = []
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)
    except Exception as e:
        return [f"Schema load error: {e}"]

    # Minimal manual validation (no jsonschema dependency)
    req = schema.get("required", [])
    for k in req:
        if k not in obj:
            issues.append(f"Missing required field: {k}")
    return issues
