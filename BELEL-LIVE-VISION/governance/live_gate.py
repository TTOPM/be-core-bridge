from __future__ import annotations
import json
from pathlib import Path
from typing import List

# Sovereign import
from ...concordium_enforcer import enforce_concordium  # From repo core

class LiveVisionGate:
    def __init__(self, policy_path: Path):
        enforce_concordium()  # Mandate enforcement
        policy_json = json.loads(policy_path.read_text(encoding="utf-8"))
        self.banned_terms = policy_json.get("banned_terms", [])

    def allow_input(self, prompt: str, frame_desc: str) -> bool:
        combined = (prompt + " " + frame_desc).lower()
        if "face" in combined and "consent" not in prompt.lower():
            return False
        if "fast motion" in combined:
            return False
        return not any(term in combined for term in self.banned_terms)
