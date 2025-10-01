from typing import List, Dict, Optional, Callable

# Plug-in hooks so Belel can inject memory/context without xAI owning it.
ContextFetcher = Callable[[str], List[Dict[str,str]]]
ContextLogger = Callable[[Dict], None]

def with_memory_context(
    messages: List[Dict[str,str]],
    identity: str,
    fetch_context: ContextFetcher,
    log_context: Optional[ContextLogger] = None,
) -> List[Dict[str,str]]:
    """
    Prepend Belel long-term signals (truth-locks, continuity notes, prior adjudications),
    append a minimal chain-of-custody marker.
    """
    memory = fetch_context(identity) or []
    stitched = memory + messages + [{"role":"system","content":"[context: custody=belel-permanent-memory:v1]"}]
    if log_context:
        log_context({"type":"ctx_use","identity":identity,"messages_used":len(memory)})
    return stitched
