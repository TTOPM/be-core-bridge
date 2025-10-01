import json
from typing import Dict, Any, Optional
from .grok_schema import validate_schema, get_schema
from .grok_model_router import route_to_model, grok_headers
from .grok_rate_limit import resilient_post

def structured_chat(
    xai_url: str,
    api_key: str,
    messages: list[Dict[str, str]],
    schema_kind: str,
    task_type: str = "analysis",
    complexity_score: int = 50,
    extra_headers: Optional[Dict[str,str]] = None
) -> Dict[str, Any]:
    """
    Ask Grok to return JSON matching our declared schema; fail closed if invalid.
    """
    model = route_to_model(task_type, complexity_score)
    body = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object", "schema": get_schema(schema_kind)}  # aligns with structured output
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        **grok_headers(model),
        **(extra_headers or {})
    }
    resp = resilient_post(f"{xai_url}/chat/completions", json=body, headers=headers)
    if "choices" not in resp or not resp["choices"]:
        raise RuntimeError("grok_no_choices")
    raw = resp["choices"][0]["message"]["content"]
    data = json.loads(raw) if isinstance(raw, str) else raw
    validate_schema(schema_kind, data)
    return data
