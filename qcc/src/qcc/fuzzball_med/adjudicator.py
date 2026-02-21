from __future__ import annotations

from typing import Any, Dict

import torch
from torch import Tensor

from ..quantum_head.entangled_verity_lattice import EntangledVerityLattice


def adjudicate_quantum_claim(
    claim: Dict[str, Any],
    lattice: EntangledVerityLattice,
    claim_queries: Tensor,
    claim_keys: Tensor,
    d_k: int = 512,
    affirm_threshold: float = 0.95,
) -> str:
    """
    FUZZBALL-MED Adjudicator

    If max verity score > 0.95:
      "Affirmed in Phase Harmony"
    else:
      "Quarantined in Fuzzball"
    """
    verity_score = lattice.entangle_order(claim_queries, claim_keys, d_k=d_k)

    # Ensure tensor is valid.
    if verity_score.numel() == 0:
        return "Quarantined in Fuzzball"

    if float(torch.max(verity_score).item()) > affirm_threshold:
        return "Affirmed in Phase Harmony"
    return "Quarantined in Fuzzball"