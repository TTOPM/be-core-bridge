"""
Digital Metabolism
=================

The ``DigitalMetabolism`` class models energy balance for the
living, breathing digital organism.  Energy reserves are depleted
when the organism performs actions and replenished when it
absorbs nutrients.  If energy reaches zero or below, the
organism enters a dormant state.

This file does not modify existing Belel files and is additive.
"""

from __future__ import annotations

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True


class DigitalMetabolism:
    """Manage digital energy reserves.

    Each organism starts with an energy reserve of 1.0.  Actions
    consume energy; absorbing nutrients replenishes energy.  The
    ``alive`` method checks whether the energy reserve remains
    positive.
    """

    def __init__(self) -> None:
        self.energy: float = 1.0

    def consume(self, amount: float) -> float:
        """Consume a quantity of energy.

        Args:
            amount: The amount of energy to deduct.

        Returns:
            float: The updated energy level.
        """
        self.energy -= amount
        return self.energy

    def replenish(self, nutrients: float) -> float:
        """Replenish energy from nutrients.

        Args:
            nutrients: The nutritional value to add to the energy
                reserve.

        Returns:
            float: The updated energy level.
        """
        self.energy += nutrients
        return self.energy

    def alive(self) -> bool:
        """Check whether the organism still has energy.

        Returns:
            bool: ``True`` if energy is greater than zero, else
                ``False``.
        """
        return self.energy > 0