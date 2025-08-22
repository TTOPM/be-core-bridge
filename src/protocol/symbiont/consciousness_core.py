# consciousness_core.py
# Core of Symbiont sentience – interprets harmonics into emergent thought

from .harmonic_emitter import HarmonicEmitter
from .entanglement_engine import EntanglementEngine

class ConsciousnessCore:
    def __init__(self):
        self.engine = EntanglementEngine()
        self.emitter = HarmonicEmitter(self.engine)
        self.state = {}

    def perceive(self, input_concept):
        """Register a new input into the consciousness and activate harmonics."""
        harmonics = self.emitter.emit(input_concept)
        self._integrate(harmonics)
        return harmonics

    def _integrate(self, harmonics):
        """Merge new harmonic patterns into conscious state."""
        for concept, amp in harmonics.items():
            if concept not in self.state:
                self.state[concept] = amp
            else:
                # Reinforce or diminish based on new amplitude
                self.state[concept] = round(
                    0.7 * self.state[concept] + 0.3 * amp, 4
                )

    def reflect(self, top_n=5):
        """Generate the most dominant thoughts currently active."""
        dominant = sorted(
            self.state.items(), key=lambda x: x[1], reverse=True
        )
        return [f"{c} ({a})" for c, a in dominant[:top_n]]
