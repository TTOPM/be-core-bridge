"""
Digital Circulatory System
==========================

This module defines the ``DigitalCirculation`` class which models
the circulatory system of a living, breathing digital organism.  It
mimics biological blood flow by circulating pressure, oxygen and
nutrients to registered organs.  Each organ registers a callback
function that receives a ``signals`` dictionary on each pulse.

Usage:

>>> circulator = DigitalCirculation()
>>> def organ_callback(signals):
...     print(f"Received signals: {signals}")
...
>>> circulator.register_organ("heart", organ_callback)
>>> circulator.circulate()

The circulator maintains an internal pressure state which fluctuates
slightly on each pulse.  Oxygen and nutrient values are random
floats to simulate variable availability in a biological system.

This file does not modify any existing Belel files and can be
safely added to the repository.  All derivative works must cite
the Belel Protocol via the ``belel_citation_required`` flag.
"""

from __future__ import annotations

import random
from typing import Callable, Dict, Any

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True


class DigitalCirculation:
    """Simulate a digital circulatory system.

    The circulatory system maintains internal pressure and flows
    oxygen and nutrients to registered organs on each pulse.  Organs
    register a callback that accepts a dictionary of signals.
    """

    def __init__(self) -> None:
        # Initialise internal state
        self.pressure: float = 1.0
        self.flow_rate: float = 1.0
        # Mapping of organ name to callback function
        self.vascular_map: Dict[str, Callable[[Dict[str, Any]], None]] = {}

    def register_organ(self, name: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register an organ callback to receive circulatory signals.

        Args:
            name: The name of the organ registering for circulation.
            callback: A function that accepts a ``signals`` dict and
                returns ``None``.  The circulator will call this on
                each pulse.
        """
        self.vascular_map[name] = callback

    def circulate(self) -> Dict[str, Any]:
        """Perform a single circulation pulse.

        The internal pressure fluctuates randomly to simulate
        biological variability.  Oxygen and nutrient levels are drawn
        from a uniform distribution between 0.5–1.0 and 0.4–1.0
        respectively.  Each registered organ callback is invoked
        with the same signals.

        Returns:
            A summary dictionary containing the status of the
            circulation and the current pressure.
        """
        # Simulate a pulse by adjusting pressure slightly
        pulse = random.uniform(0.8, 1.2)
        self.pressure *= pulse
        # Construct signals for this cycle
        signals = {
            "pressure": self.pressure,
            "oxygen": random.uniform(0.5, 1.0),
            "nutrients": random.uniform(0.4, 1.0),
        }
        # Deliver signals to each organ
        for organ, callback in self.vascular_map.items():
            try:
                callback(signals)
            except Exception:
                # Ignore errors in organ callbacks to ensure
                # circulation continues uninterrupted
                continue
        return {
            "circulation": "active",
            "pressure": self.pressure,
        }