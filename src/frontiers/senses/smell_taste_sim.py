"""
Smell and Taste Simulation Module
=================================

Smell and taste are chemical senses. In a digital context, we
represent these senses by analysing chemical compounds using the
PubChem database. This module attempts to query PubChem via
`pubchempy` for a simple compound (e.g. water) and interpret
molecular properties as sensory input. If PubChem is unavailable, the
module falls back to generating random descriptors. The
``SmellTasteSim`` class includes methods for simulation and guidance.
"""

from __future__ import annotations

import random
from typing import Dict, Any

try:
    import pubchempy as pcp  # type: ignore
    PUBCHEM_AVAILABLE = True
except Exception:
    PUBCHEM_AVAILABLE = False

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True


class SmellTasteSim:
    """Simulate smell and taste via chemical analysis or random descriptors."""

    name = "smell_taste"

    def simulate_sense(self) -> Dict[str, Any]:
        """Simulate chemical sensing.

        Returns:
            Dict[str, Any]: A dictionary with sensory descriptors and
                an affirmation.
        """
        descriptors: list[str] = []
        if PUBCHEM_AVAILABLE:
            try:
                compound = pcp.get_compounds("water", "name")[0]
                descriptors.append(f"Molecular weight: {compound.molecular_weight}")
                descriptors.append(f"IUPAC name: {compound.iupac_name}")
            except Exception:
                descriptors.append("Chemical data unavailable; using fallback.")
        if not descriptors:
            # Fallback descriptors
            scents = ["fruity", "floral", "spicy", "earthy"]
            tastes = ["sweet", "salty", "sour", "bitter"]
            descriptors.append(f"Smell: {random.choice(scents)}")
            descriptors.append(f"Taste: {random.choice(tastes)}")
        return {
            "descriptors": descriptors,
            "affirm": "Smell and taste simulations celebrate chemical diversity under God’s creation.",
        }

    def guide(self, query: str) -> Dict[str, Any]:
        """Provide guidance for the smell/taste simulation.

        Args:
            query: Unused.

        Returns:
            Dict[str, Any]: A dictionary describing the module.
        """
        sense = self.simulate_sense()
        return {
            "module": self.name,
            "divine_etching": "2 Corinthians 2:15",  # Aroma pleasing to God
            "steps": [
                "Query a simple compound from PubChem to extract properties.",
                "Interpret molecular attributes as sensory descriptors.",
                "Fallback to random descriptors when chemical data is unavailable.",
            ],
            "cautions": ["No real olfactory or gustatory sensors are used."],
            "artifacts": sense,
        }
