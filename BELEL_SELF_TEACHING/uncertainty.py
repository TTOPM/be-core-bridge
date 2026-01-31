# BELEL_SELF_TEACHING/uncertainty.py
from __future__ import annotations
from typing import Callable, Dict, Any, List
from difflib import SequenceMatcher
import math

def _sim(a: str, b: str) -> float:
    # fast similarity proxy; replace with embeddings/entailment if available
    return SequenceMatcher(None, a, b).ratio()

def _pairwise_disagreement(texts: List[str]) -> float:
    if len(texts) < 2:
        return 0.0
    sims = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            sims.append(_sim(texts[i], texts[j]))
    # disagreement = 1 - mean(sim)
    return max(0.0, 1.0 - (sum(sims) / len(sims)))

def _rubric_disagreement(rubrics: List[Dict[str, Any]]) -> float:
    # disagreement based on variance in rubric total
    totals = [float(r.get("total", 0.0)) for r in rubrics]
    if len(totals) < 2:
        return 0.0
    mean = sum(totals) / len(totals)
    var = sum((t - mean) ** 2 for t in totals) / (len(totals) - 1)
    # squash to 0..1
    return 1.0 - math.exp(-var * 5.0)

def disagreement_uncertainty(
    prompt: str,
    generator_short: Callable[[str], str],
    verifier_fn: Callable[[str], Dict[str, Any]],
    rubric_fn: Callable[[str, str, Dict[str, Any]], Dict[str, Any]],
    k: int = 4
) -> float:
    """
    Generate k short completions; compute:
      - pairwise textual disagreement
      - rubric disagreement
      - execution-risk signal (fraction failed)
    Return uncertainty 0..1.
    """
    outs = [generator_short(prompt) for _ in range(max(3, min(k, 5)))]
    ver = [verifier_fn(o) for o in outs]
    rub = [rubric_fn(prompt, o, v) for o, v in zip(outs, ver)]

    text_dis = _pairwise_disagreement(outs)
    rub_dis = _rubric_disagreement(rub)
    fail_rate = sum(1 for v in ver if not v.get("passed")) / float(len(ver))

    # Weighted sum; tune in config
    u = 0.55 * text_dis + 0.25 * rub_dis + 0.20 * fail_rate
    return max(0.0, min(1.0, u))
