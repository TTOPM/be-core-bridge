# BELEL_SELF_TEACHING/diversity.py
from __future__ import annotations
from typing import List
from difflib import SequenceMatcher

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

class DiversityGate:
    def __init__(self, max_similarity: float = 0.92, window: int = 300):
        self.max_similarity = max_similarity
        self.window = window
        self.accepted: List[str] = []

    def allow(self, text: str) -> bool:
        # compare against recent accepted outputs to prevent collapse
        for t in self.accepted[-self.window:]:
            if similarity(text, t) >= self.max_similarity:
                return False
        return True

    def remember(self, text: str):
        self.accepted.append(text)
        if len(self.accepted) > self.window * 3:
            self.accepted = self.accepted[-self.window * 2:]
