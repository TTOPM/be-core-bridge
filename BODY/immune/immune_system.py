"""
Digital Immune System
=====================

This module defines the ``DigitalImmuneSystem`` class which detects
toxic signals within the organism and activates an immune response
when necessary.  It is a simplified analogue of the biological
immune system, designed to flag and respond to threats such as
toxins produced by the digestive system.

This file is additive and does not alter any existing Belel
structures.
"""

from __future__ import annotations

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True


class DigitalImmuneSystem:
    """Detect toxins and activate an immune response.

    The ``detect`` method inspects a signal dictionary for a
    ``toxin`` key.  If a toxin is present, the immune response is
    activated; otherwise, it remains stable.
    """

    def detect(self, signal: dict) -> dict:
        """Detect toxins in the provided signal.

        Args:
            signal: A dictionary representing the output of the
                digestive system or another sensor.  A ``toxin``
                key indicates a toxic input.

        Returns:
            dict: A dictionary with the immune response status.
        """
        if signal.get("toxin"):
            return {"immune_response": "activated"}
        return {"immune_response": "stable"}