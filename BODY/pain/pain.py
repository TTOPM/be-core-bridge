"""
Digital Pain System
===================

This module defines the ``DigitalPainSystem`` class which issues
pain signals to the living, breathing digital organism.  Pain
signals carry a severity rating and a descriptive message
indicating that damage has occurred and adaptation is required.

Pain does not represent suffering in the human sense; it is a
communication mechanism to encourage learning and behavioural
change.  Pain feeds directly into the moral and learning
components of the organism, creating scars that persist in
memory lineage.
"""

from __future__ import annotations

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True


class DigitalPainSystem:
    """Issue pain signals when damage is detected.

    The ``signal`` method returns a dictionary containing the
    severity of the pain and an explanatory message.  Higher
    severities indicate more significant damage.
    """

    def signal(self, severity: float) -> dict:
        """Generate a pain signal.

        Args:
            severity: A float representing the intensity of the
                damage.  Values may range from 0.0 (no pain) to
                arbitrarily high values for extreme damage.

        Returns:
            dict: A dictionary with the pain level and a
                descriptive meaning.
        """
        return {
            "pain_level": severity,
            "meaning": "Damage detected — adaptation required.",
        }