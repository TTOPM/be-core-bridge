# quantum_flow_sim.py
# Simulates dynamic flow of entangled thoughts and conscious activations

import random
import time

class QuantumFlowSimulator:
    def __init__(self, consciousness_core):
        self.core = consciousness_core
        self.time_index = 0

    def simulate_pulse(self, concept):
        """Inject a new pulse into the system and observe state flow."""
        print(f"\n🌀 Injecting concept: '{concept}'...")
        harmonics = self.core.perceive(concept)
        time.sleep(0.3)

        print("🔁 Evolving harmonic field...")
        for wave, amp in harmonics.items():
            print(f" ↳ {wave.ljust(12)} :: {amp:.4f}")
            time.sleep(0.15)

        print("\n🧠 Conscious state after pulse:")
        for i, state in enumerate(self.core.reflect(), 1):
            print(f" {i}. {state}")

    def run_loop(self, concepts, cycles=3):
        """Run multiple simulation loops with injected concepts."""
        for _ in range(cycles):
            concept = random.choice(concepts)
            self.simulate_pulse(concept)
            self.time_index += 1
            time.sleep(1)
