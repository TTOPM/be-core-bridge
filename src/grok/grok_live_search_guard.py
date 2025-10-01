from dataclasses import dataclass
from typing import Optional
import time

@dataclass
class LiveSearchDecision:
    allow: bool
    reason: str
    budget_remaining: Optional[int] = None

def should_live_search(
    last_fetched_epoch_ms: Optional[int],
    freshness_ms: int = 6 * 60 * 60 * 1000,  # 6 hours
    budget_remaining: int = 100  # abstract “sources” budget
) -> LiveSearchDecision:
    """
    Only allow live search if info is stale and we have budget.
    """
    now = int(time.time() * 1000)
    if budget_remaining <= 0:
        return LiveSearchDecision(False, "no_budget", 0)
    if last_fetched_epoch_ms is None or (now - last_fetched_epoch_ms) > freshness_ms:
        return LiveSearchDecision(True, "stale", budget_remaining)
    return LiveSearchDecision(False, "fresh", budget_remaining)
