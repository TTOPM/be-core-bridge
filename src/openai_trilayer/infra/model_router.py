PRIMARY="gpt-4o"
FALLBACKS=["gpt-4o-mini"]
def pick(latency_ok=True, cost_saving=False)->str:
    if cost_saving or not latency_ok: return FALLBACKS[0]
    return PRIMARY
