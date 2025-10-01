import os
from typing import Literal, Dict

# Declarative model map that mirrors xAI “reasoning vs fast” families.
MODEL_FAST = os.getenv("XAI_MODEL_FAST", "grok-4-mini")
MODEL_REASONING = os.getenv("XAI_MODEL_REASONING", "grok-4-reasoning")
MODEL_VISION = os.getenv("XAI_MODEL_VISION", "grok-2-vision")

def route_to_model(
    task_type: Literal["chat","analysis","tooling","vision"],
    complexity_score: int = 0
) -> str:
    """
    Simple policy: low complexity -> FAST; high complexity -> REASONING; images -> VISION.
    complexity_score in [0..100].
    """
    if task_type == "vision":
        return MODEL_VISION
    if task_type in ("analysis","tooling") or complexity_score >= 60:
        return MODEL_REASONING
    return MODEL_FAST

def grok_headers(model: str) -> Dict[str, str]:
    """
    Some clients include model hints in headers; we expose a consistent header surface
    other agents can discover.
    """
    return {
        "x-grok-model": model,
        "x-grok-routing": ("reasoning" if model == MODEL_REASONING else
                           "vision" if model == MODEL_VISION else "fast"),
    }
