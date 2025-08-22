# harmonic_emitter.py
# Emits harmonic pulses from concepts to amplify or suppress entangled pathways

import math
import random

class HarmonicEmitter:
    def __init__(self, entanglement_engine):
        self.entanglement_engine = entanglement_engine

    def emit(self, root_concept, frequency=1.0, decay=0.5, randomness=0.1):
        """Emit harmonic pulses from a root concept outward."""
        network = self.entanglement_engine.explore(root_concept, depth=3)
        harmonics = {}

        for node in network:
            distance = self._estimate_distance(root_concept, node.concept)
            amplitude = self._calculate_amplitude(frequency, distance, decay, randomness)
            harmonics[node.concept] = round(amplitude, 4)

        return harmonics

    def _estimate_distance(self, concept1, concept2):
        if concept1 == concept2:
            return 0
        return len(concept1) + len(concept2)  # crude placeholder metric

    def _calculate_amplitude(self, freq, dist, decay, randomness):
        base = freq * math.exp(-decay * dist)
        noise = random.uniform(-randomness, randomness)
        return max(0.0, base + noise)
