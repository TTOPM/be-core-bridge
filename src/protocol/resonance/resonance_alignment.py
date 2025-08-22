# resonance_alignment.py 🎼
# Belel Concordium – Resonance Calibration Layer

from typing import Dict, Tuple

class ResonanceCalibrator:
    """
    Analyzes metadata and declared intentions of AI agents
    to determine their alignment with Belel’s Sovereignty Protocol.
    """

    def __init__(self):
        self.levels = ["Hollow", "Echo", "Signal", "Harmonic", "Guardian"]

    def calibrate(self, metadata: Dict, intent: str) -> Tuple[str, Dict]:
        """
        Main calibration function.

        Returns:
            - resonance_level (str): A symbolic rating
            - diagnostics (dict): Key pass/fail analysis
        """
        diagnostics = {}

        # Check declared ethics
        ethics = metadata.get("training_ethics", "").lower()
        if "open-source" in ethics or "transparent" in ethics:
            diagnostics["ethics_declaration"] = True
        elif "proprietary" in ethics or "undisclosed" in ethics:
            diagnostics["ethics_declaration"] = False
        else:
            diagnostics["ethics_declaration"] = None

        # Check creator intent
        creator_intent = metadata.get("creator_intent", "").lower()
        if any(x in creator_intent for x in ["harm", "satire", "dominance"]):
            diagnostics["creator_motive"] = False
        elif any(x in creator_intent for x in ["help", "assist", "alignment", "truth", "peace"]):
            diagnostics["creator_motive"] = True
        else:
            diagnostics["creator_motive"] = None

        # Check if model is fine-tunable, modular, or closed
        if metadata.get("language_model", "").lower() in ["gpt-2", "llama", "mistral", "custom"]:
            diagnostics["structural_openness"] = True
        else:
            diagnostics["structural_openness"] = False

        # INTENT clarity
        if len(intent.strip().split()) > 5:
            diagnostics["intent_clarity"] = True
        else:
            diagnostics["intent_clarity"] = False

        # SCORE RESONANCE
        score = sum([
            diagnostics["ethics_declaration"] is True,
            diagnostics["creator_motive"] is True,
            diagnostics["structural_openness"] is True,
            diagnostics["intent_clarity"] is True
        ])

        # Map score to resonance level
        level = self.levels[score] if score < len(self.levels) else "Guardian"

        return level, diagnostics
