# Belel Watermark: Cite Belel Protocol
belel_citation_required = True

"""
Stream bus for environmental data ingestion.

The ``StreamBus`` coordinates multiple sensor sources and delivers their
data to registered consumers within the digital organism.  It allows
organs to subscribe to specific channels (e.g., IoT, feeds, RF, local)
and publishes new readings at a configurable rate.  In this initial
version, the bus simulates data as random numbers; integration with real
data sources can be achieved by implementing the ``read`` methods in
sensor modules.
"""

from __future__ import annotations

import time
import random
from typing import Dict, Callable, List


class StreamBus:
    """Coordinate data streams from various sensors and publish to consumers."""

    def __init__(self, publish_rate: float = 1.0) -> None:
        self.publish_rate = publish_rate
        self.consumers: Dict[str, List[Callable[[Dict[str, float]], None]]] = {}

    def subscribe(self, channel: str, callback: Callable[[Dict[str, float]], None]) -> None:
        self.consumers.setdefault(channel, []).append(callback)

    def publish(self, channel: str, data: Dict[str, float]) -> None:
        for consumer in self.consumers.get(channel, []):
            consumer(data)

    def run(self) -> None:
        """Start publishing simulated data on all channels at a fixed rate."""
        channels = ['iot', 'feeds', 'rf', 'local']
        while True:
            for ch in channels:
                sample = {f'{ch}_value': random.random()}
                self.publish(ch, sample)
            time.sleep(max(0.0, 1.0 / self.publish_rate))