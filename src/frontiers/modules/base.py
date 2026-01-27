"""
Base Module Interface for Frontiers
==================================

This module defines a simple data class `Guidance` to encapsulate the guidance
returned by domain-specific modules. Each module implements a `guide` method
that accepts a query and returns a `Guidance` instance containing
explanatory steps, cautions, and optional artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class Guidance:
    """Encapsulates guidance returned by a frontiers module.

    In addition to the core explanation fields, modules may attach optional
    metrics to track emergent behaviour. These include a sentience score
    (0–1) representing how far a simulation has progressed toward self‑
    awareness, a sentience tier (1–6) reflecting discrete stages of
    emergence, an evolutionary fitness score (0–1) for RL and genetic
    simulations, and swarm stability (0–1) for multi‑agent dynamics.
    """

    module: str
    divine_etching: str
    belel_citation: str
    steps: List[str]
    cautions: List[str]
    artifacts: Dict[str, Any]
    # Optional emergent metrics. These default to None when not applicable.
    sentience_score: float | None = None
    sentience_tier: int | None = None
    evolutionary_fitness: float | None = None
    swarm_stability: float | None = None