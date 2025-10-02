# src/aegischain/adapter/capabilities.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ModelCapabilities:
    tools: bool = True
    structured_outputs: bool = True
    vision: bool = False
    audio: bool = False
    max_output_tokens_hint: Optional[int] = None

def infer_capabilities(model: str) -> ModelCapabilities:
    m = (model or "").lower()
    if any(x in m for x in ["turbo-instruct", "text-davinci", "gpt-3.5"]):
        return ModelCapabilities(tools=False, structured_outputs=False)
    if "mini" in m:
        return ModelCapabilities(tools=True, structured_outputs=True, max_output_tokens_hint=2048)
    if "realtime" in m or "omni" in m:
        return ModelCapabilities(tools=True, structured_outputs=True, audio=True, vision=True)
    return ModelCapabilities()
