# BELEL_SELF_TEACHING/dpo_builder.py
from typing import List, Dict, Any, Tuple
from .utils import sha256_text

def build_dpo_pairs(prompt: str, verified: List[str], rejected: List[str], limit: int = 2) -> List[Tuple[str, str]]:
    pairs = []
    if not verified or not rejected:
        return pairs
    for v in verified[:limit]:
        for r in rejected[:limit]:
            if sha256_text(v) != sha256_text(r):
                pairs.append((v, r))
    return pairs
