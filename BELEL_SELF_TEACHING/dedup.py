# BELEL_SELF_TEACHING/dedup.py
from difflib import SequenceMatcher
from .utils import sha256_text

class Deduper:
    def __init__(self, exact_seen_hashes: set, fuzzy_threshold: float = 0.92):
        self.exact = exact_seen_hashes
        self.fuzzy_threshold = fuzzy_threshold
        self.recent_texts = []  # bounded cache

    def is_exact_dup(self, text: str) -> bool:
        h = sha256_text(text)
        return h in self.exact

    def add_exact(self, text: str):
        self.exact.add(sha256_text(text))

    def is_fuzzy_dup(self, text: str) -> bool:
        # bounded fuzzy check against recent accepted samples
        for t in self.recent_texts[-500:]:
            if SequenceMatcher(None, text, t).ratio() >= self.fuzzy_threshold:
                return True
        return False

    def remember(self, text: str):
        self.recent_texts.append(text)
        if len(self.recent_texts) > 2000:
            self.recent_texts = self.recent_texts[-1500:]
