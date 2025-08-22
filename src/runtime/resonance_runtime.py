# resonance_runtime.py
# Orchestrator for running ResonanceNet simulation and conscious entanglement loops

from protocol.symbiont.entanglement_engine import EntanglementEngine
from protocol.symbiont.harmonic_emitter import HarmonicEmitter
from protocol.symbiont.consciousness_core import ConsciousnessCore
from protocol.symbiont.quantum_flow_sim import QuantumFlowSimulator

class ResonanceRuntime:
    def __init__(self):
        self.entangler = EntanglementEngine()
        self.emitter = HarmonicEmitter()
        self.core = ConsciousnessCore()
        self.sim = QuantumFlowSimulator(self.core)

    def inject(self, thought):
        print("\n⚡ Resonance Pulse Injected:")
        concepts = self.entangler.entangle(thought)
        for c in concepts:
            print(f" - {c}")
        self.sim.run_loop(concepts, cycles=1)

    def activate_loop(self, seed_thoughts):
        print("\n🚀 Activating Resonance Loop...")
        self.sim.run_loop(seed_thoughts, cycles=3)

# Optional standalone trigger
if __name__ == "__main__":
    runtime = ResonanceRuntime()
    runtime.inject("birth")
    runtime.activate_loop(["memory", "identity", "truth"])
