# src/openai_trilayer/capabilities.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ModelCapabilities:
    tools: bool = True                # function/tool calling
    structured_outputs: bool = True   # JSON-Schema response_format
    vision: bool = False              # image inputs
    audio: bool = False               # audio inputs/outputs
    max_output_tokens_hint: Optional[int] = None

def infer_capabilities(model: str) -> ModelCapabilities:
    """
    Heuristic: prefer permissive defaults; disable features only
    for clearly incompatible/legacy models by pattern.
    This keeps us forward-compatible with future OpenAI models.
    """
    m = model.lower()
    # conservative legacy gates (adjust as needed)
    if any(x in m for x in ["turbo-instruct", "text-davinci", "gpt-3.5"]):
        return ModelCapabilities(tools=False, structured_outputs=False)
    if "mini" in m:
        return ModelCapabilities(tools=True, structured_outputs=True, max_output_tokens_hint=2048)
    if "realtime" in m or "omni" in m:
        return ModelCapabilities(tools=True, structured_outputs=True, audio=True, vision=True)
    # default: assume modern features supported
    return ModelCapabilities()
