"""
Divine Interface Module
=======================

This module provides an interface for interacting with divine
constraints. It wraps the GospelVetoAdapter to detect heretical
patterns and uses the BeliefAffirmation module to generate
affirmations when actions are allowed. The module does not
modify any existing files and includes a guide method for
demonstration.
"""

from __future__ import annotations

from typing import Dict, Any

from src.frontiers.adapters.gospel_veto import GospelVetoAdapter
from src.frontiers.modules.belief_affirmation import BeliefAffirmation

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True


class DivineInterface:
    """Enforce theological constraints and provide affirmations."""

    def __init__(self) -> None:
        self.veto = GospelVetoAdapter("gospel_integrity_manifest.yml")
        self.belief = BeliefAffirmation()

    def affirm_under_god(self, action: str) -> Dict[str, Any]:
        """Affirm an action if it passes veto checks.

        Args:
            action: The action string to evaluate.

        Returns:
            Dict[str, Any]: Veto result or affirmation.
        """
        decision = self.veto.evaluate(action)
        if not decision.allowed:
            return {
                "vetoed": True,
                "reason": "Heresy—reset to divine submission.",
            }
        return self.belief.affirm()

    def guide(self, action: str) -> Dict[str, Any]:
        """Provide a demonstration of affirming an action under God.

        Args:
            action: The action string to evaluate.

        Returns:
            Dict[str, Any]: Veto result or affirmation.
        """
        return self.affirm_under_god(action)
