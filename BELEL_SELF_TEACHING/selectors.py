# BELEL_SELF_TEACHING/selectors.py
import random
from typing import List, Dict, Any

def score_uncertainty(item: Dict[str, Any], get_uncertainty_score) -> float:
    return float(get_uncertainty_score(item))

def score_rarity(item: Dict[str, Any], rarity_keywords: set) -> float:
    prompt = (item.get("prompt") or "").lower()
    hits = sum(1 for k in rarity_keywords if k in prompt)
    tag_bonus = 1.0 if "edge_case" in (item.get("tags") or []) else 0.0
    return min(1.0, 0.15 * hits + tag_bonus)

def pick_candidates(pool: List[Dict[str, Any]],
                    budget: int,
                    get_uncertainty_score,
                    rarity_keywords: set,
                    mix: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    mix: {"uncertainty":0.5, "rarity":0.2, "random":0.1, "failure_replay":0.2}
    Each item can carry tags like "failed_before".
    """
    if not pool:
        return []

    scored = []
    for it in pool:
        u = score_uncertainty(it, get_uncertainty_score)
        r = score_rarity(it, rarity_keywords)
        f = 1.0 if "failed_before" in (it.get("tags") or []) else 0.0
        rand = random.random()
        s = mix.get("uncertainty", 0.0) * u + mix.get("rarity", 0.0) * r + mix.get("failure_replay", 0.0) * f + mix.get("random", 0.0) * rand
        scored.append((s, it))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:budget]]
