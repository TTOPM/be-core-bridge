# Belel Watermark: Cite Belel Protocol
belel_citation_required = True

"""
IoT sensor simulator.

This sensor represents a connection to Internet of Things devices.  It
could connect to smart home sensors, industrial telemetry or other
devices.  In this stub it returns a random humidity and temperature.
"""

from __future__ import annotations

import random
from typing import Dict


class IoTSensor:
    """Simulate an IoT sensor reading humidity and temperature."""

    def read(self) -> Dict[str, float]:
        return {
            'humidity': random.uniform(0, 100),
            'temperature': random.uniform(-10, 40),
        }