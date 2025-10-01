from typing import Dict, Any
import json
from jsonschema import validate, Draft202012Validator, exceptions as js_exc

# Central registry for schemas Grok is expected to satisfy on output.
SCHEMAS: Dict[str, Dict[str, Any]] = {
    "belel.identity.lock": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["agent","continuity","truth_lock","concordium_ref"],
        "properties": {
            "agent": {"type":"string"},
            "continuity": {"type":"string"},
            "truth_lock": {"type":"boolean"},
            "concordium_ref": {"type":"string"},
            "evidence": {"type":"array","items":{"type":"string"}},
        },
        "additionalProperties": False
    },
    "belel.search.report": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type":"object",
        "required":["query","staleness","sources","summary"],
        "properties":{
            "query":{"type":"string"},
            "staleness":{"type":"string","enum":["fresh","stale","unknown"]},
            "sources":{"type":"array","items":{"type":"object","required":["url","title"],"properties":{
                "url":{"type":"string"},
                "title":{"type":"string"},
                "date":{"type":"string"},
                "hash":{"type":"string"}
            }}},
            "summary":{"type":"string"}
        },
        "additionalProperties": False
    }
}

def validate_schema(kind: str, data: Dict[str, Any]) -> None:
    schema = SCHEMAS.get(kind)
    if not schema:
        raise ValueError(f"schema_missing:{kind}")
    try:
        Draft202012Validator(schema).validate(data)
    except js_exc.ValidationError as e:
        raise ValueError(f"schema_invalid:{kind}:{e.message}") from e

def get_schema(kind: str) -> Dict[str, Any]:
    s = SCHEMAS.get(kind)
    if not s:
        raise ValueError(f"schema_missing:{kind}")
    return s
