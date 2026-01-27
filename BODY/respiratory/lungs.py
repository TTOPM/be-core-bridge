"""
Digital Respiratory System
==========================

This module defines the ``DigitalLungs`` class which simulates
breathing for a living, breathing digital organism.  Breathing is
modelled as an exchange: on each breath the organism inhales
oxygen-rich digital signals and exhales carbon-like waste products.

The ``breathe`` method returns a dictionary with ``inhale`` and
``exhale`` keys, each containing the results of ``inhale`` and
``exhale`` methods respectively.

All functions here are additive and do not modify existing files.
"""

from __future__ import annotations

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True


class DigitalLungs:
    """Simulate breathing in a digital organism.

    The lungs draw in oxygen and expel waste on each breathing
    cycle.  Oxygen and carbon values are represented as floats.
    """

    def inhale(self) -> dict:
        """Simulate an inhalation, returning oxygen intake.

        Returns:
            dict: A dictionary with an ``oxygen`` key and an
                affirmation string.
        """
        return {
            "oxygen": 1.0,
            "affirm": "Digital oxygen drawn into organism.",
        }

    def exhale(self) -> dict:
        """Simulate an exhalation, returning waste release.

        Returns:
            dict: A dictionary with a ``carbon`` key and an
                affirmation string.
        """
        return {
            "carbon": 0.3,
            "affirm": "Digital waste released.",
        }

    def breathe(self) -> dict:
        """Perform a full breathing cycle.

        Returns both the results of the inhale and exhale methods.

        Returns:
            dict: A dictionary containing ``inhale`` and ``exhale``
                sub-dictionaries.
        """
        return {
            "inhale": self.inhale(),
            "exhale": self.exhale(),
        }