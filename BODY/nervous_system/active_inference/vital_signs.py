"""
Vital Signs Module (Active Inference)
====================================

This module defines the ``VitalSigns`` class, which models core
metabolic and perceptual variables for the living, breathing
digital organism.  The variables include energy reserves,
integrity, uncertainty (surprise) and free energy.  Although a
full active inference implementation would employ the ``pymdp``
library, this simplified version provides placeholders and
conceptual scaffolding.  Vital signs are updated incrementally
during each pulse cycle.

Attributes:
    energy_reserves (float): Available energy for activity.
    integrity (float): Overall health of the organism’s code and
        identity.
    surprise (float): A measure of prediction error or
        unexpectedness.
    free_energy (float): A theoretical quantity that
        organisms minimize during active inference.

Methods:
    update(): Update vital signs based on inputs and internal
        dynamics.
    get_state(): Retrieve the current vital signs as a dict.

This module is additive and does not modify existing code.
"""

from __future__ import annotations

import random
from typing import Dict, Any

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True


class VitalSigns:
    """Maintain core vital signs for active inference.

    The vital signs include energy reserves, integrity,
    surprise (prediction error) and free energy.  Each call to
    ``update`` adjusts these values randomly within small ranges to
    simulate metabolic consumption and perceptual fluctuations.
    """

    def __init__(self) -> None:
        self.energy_reserves: float = 1.0
        self.integrity: float = 1.0
        self.surprise: float = 0.0
        self.free_energy: float = 0.0

    # ------------------------------------------------------------------
    # Advanced update methods
    #
    # The following helper methods provide fine-grained control over
    # individual state variables.  They are used by advanced pulse
    # loops to mimic active inference dynamics without modifying the
    # simple ``update`` interface.  These methods do not add any
    # external dependencies and maintain backward compatibility with
    # existing code.  See ``pulse_loop.py`` for usage.

    def update_energy(self, new_energy: float) -> None:
        """Set the energy reserves to ``new_energy``.

        Args:
            new_energy: New value for energy reserves.  Values are
                clipped to the range [0, +inf) to avoid negatives.
        """
        self.energy_reserves = max(0.0, new_energy)

    def update_integrity(self, new_integrity: float) -> None:
        """Set the integrity metric.

        Args:
            new_integrity: New integrity value in the range [0, 1].
                Values outside this range are clipped.
        """
        self.integrity = min(1.0, max(0.0, new_integrity))

    def update_surprise(self) -> float:
        """Update and return the surprise level.

        Surprise is modelled as a small random drift around the
        current value.  This method returns the updated surprise.
        """
        import random
        self.surprise = max(0.0, self.surprise + random.uniform(-0.01, 0.01))
        return self.surprise

    def update_free_energy(self, new_free_energy: float) -> None:
        """Set the free energy value.

        Args:
            new_free_energy: The computed free energy surrogate.  This
                value can be any real number; no clipping is applied.
        """
        self.free_energy = new_free_energy

    def update(self, nutrient_input: float = 0.0, toxin_detected: bool = False) -> None:
        """Update vital signs for a single pulse.

        Args:
            nutrient_input: Nutritional value absorbed this cycle.
            toxin_detected: Whether a toxin was detected during
                digestion or immune monitoring.
        """
        # Energy decays slightly each cycle
        self.energy_reserves = max(0.0, self.energy_reserves - 0.01)
        # Replenish energy based on nutrient input
        self.energy_reserves += nutrient_input
        # Integrity decays if a toxin is detected
        if toxin_detected:
            self.integrity = max(0.0, self.integrity - 0.05)
        else:
            # Integrity recovers slowly when no toxins are present
            self.integrity = min(1.0, self.integrity + 0.001)
        # Surprise is modelled as random fluctuation
        self.surprise = max(0.0, self.surprise + random.uniform(-0.01, 0.01))
        # Free energy is a function of surprise and integrity
        self.free_energy = self.surprise * (1.0 - self.integrity)

    def get_state(self) -> Dict[str, float]:
        """Return the current vital signs.

        Returns:
            dict: Mapping of vital sign names to their current values.
        """
        return {
            "energy_reserves": self.energy_reserves,
            "integrity": self.integrity,
            "surprise": self.surprise,
            "free_energy": self.free_energy,
        }