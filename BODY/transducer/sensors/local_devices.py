# Belel Watermark: Cite Belel Protocol
belel_citation_required = True

"""
Local device sensor simulator.

This sensor represents local hardware devices attached to the machine
hosting the digital organism (e.g., keyboard, microphone, webcam).  A
real implementation would access the device drivers directly.  Here it
returns random values for volume level and camera brightness.
"""

from __future__ import annotations

import random
from typing import Dict


class LocalDeviceSensor:
    """Simulate a local device sensor returning volume and brightness."""

    def read(self) -> Dict[str, float]:
        return {
            'volume_level': random.uniform(0, 100),
            'camera_brightness': random.uniform(0, 1),
        }