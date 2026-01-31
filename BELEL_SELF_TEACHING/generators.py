# BELEL_SELF_TEACHING/generators.py
import random
from typing import List, Dict, Any

def generate_variants(prompt: str, generate_reflexive_variant, n: int = 3) -> List[str]:
    outs = []
    for _ in range(n):
        outs.append(generate_reflexive_variant(prompt, mode="generate"))
    # Mutations
    for _ in range(random.randint(1, 3)):
        base = random.choice(outs)
        outs.append(generate_reflexive_variant(base, mode="mutate"))
    # Dedup inside batch
    uniq = []
    seen = set()
    for o in outs:
        if o not in seen:
            uniq.append(o); seen.add(o)
    return uniq

def self_consistency_pick(candidates: List[str]) -> List[str]:
    """
    Lightweight: return list as-is; if you add an internal scorer,
    you can rank by agreement/overlap across samples.
    """
    return candidates
