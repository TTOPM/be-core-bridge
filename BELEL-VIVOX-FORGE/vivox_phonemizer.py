cat > BELEL-VIVOX-FORGE/vivox_phonemizer.py << 'EOF'
from __future__ import annotations
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .vivox_utils import (
    ARPABET_TO_VIVOX,
    Phone,
    is_vowel,
    normalize_whitespace,
    split_words,
    strip_arpabet_stress,
)

# CMUdict line format: WORD  PH1 PH2 PH3...
# Also allows WORD(2) variants
CMUDICT_RE = re.compile(r"^([A-Z0-9']+)(\(\d+\))?\s+(.+)$")

@dataclass
class PhonemizerConfig:
    cmudict_path: str = "BELEL-VIVOX-FORGE/assets/cmudict.txt"
    use_dict: bool = True
    fallback_rules: bool = True

class CMUDict:
    def __init__(self, path: str):
        self.path = path
        self.lex: Dict[str, List[List[str]]] = {}

    def load(self) -> None:
        if not os.path.exists(self.path):
            return
        with open(self.path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(";;;"):
                    continue
                m = CMUDICT_RE.match(line)
                if not m:
                    continue
                word = m.group(1).lower()
                phones = m.group(3).strip().split()
                self.lex.setdefault(word, []).append(phones)

    def lookup(self, word: str) -> Optional[List[str]]:
        word = (word or "").lower().strip()
        if not word:
            return None
        alts = self.lex.get(word)
        if not alts:
            return None
        # Choose first variant (you can add heuristics later)
        return alts[0]

def _fallback_g2p(word: str) -> List[Phone]:
    """
    Minimal rule-based fallback that maps characters -> approximate phones.
    Not perfect. Designed to keep the system usable without cmudict.
    """
    w = word.lower()
    out: List[Phone] = []
    i = 0
    while i < len(w):
        ch = w[i]

        # digraphs
        if w[i:i+2] == "th":
            out.append(Phone("th", None, False, "th")); i += 2; continue
        if w[i:i+2] == "sh":
            out.append(Phone("sh", None, False, "sh")); i += 2; continue
        if w[i:i+2] == "ch":
            out.append(Phone("ch", None, False, "ch")); i += 2; continue
        if w[i:i+2] == "ng":
            out.append(Phone("ng", None, False, "ng")); i += 2; continue

        # vowels
        if ch in "aeiou":
            sym = {"a":"ah","e":"eh","i":"ih","o":"ow","u":"uh"}[ch]
            out.append(Phone(sym, 1, True, ch))
            i += 1
            continue

        # consonants
        m = {
            "p":"p","b":"b","t":"t","d":"d","k":"k","g":"g",
            "m":"m","n":"n","f":"f","v":"v","s":"s","z":"z","h":"h",
            "r":"r","l":"l","y":"y","w":"w",
            "j":"jh","c":"k","q":"k","x":"s",
        }.get(ch)
        if m:
            out.append(Phone(m, None, False, ch))
        i += 1

    return out or [Phone("ah", 1, True, word)]

class VivoxPhonemizer:
    def __init__(self, cfg: Optional[PhonemizerConfig] = None):
        self.cfg = cfg or PhonemizerConfig()
        self.cm = CMUDict(self.cfg.cmudict_path)
        if self.cfg.use_dict:
            self.cm.load()

    def word_to_phones(self, word: str) -> List[Phone]:
        # try dict
        if self.cfg.use_dict:
            tokens = self.cm.lookup(word)
            if tokens:
                out: List[Phone] = []
                for tok in tokens:
                    base, stress = strip_arpabet_stress(tok)
                    base = base.upper()
                    viv = ARPABET_TO_VIVOX.get(base)
                    if not viv:
                        continue
                    out.append(Phone(viv, stress, is_vowel(viv), tok))
                if out:
                    return out
        # fallback
        if self.cfg.fallback_rules:
            return _fallback_g2p(word)
        return [Phone("ah", 1, True, word)]

    def phonemize(self, text: str) -> List[Phone]:
        """
        Returns a linear phone stream with:
        - '|' boundaries between words
        - 'sil' pauses for punctuation
        """
        text = normalize_whitespace(text)
        if not text:
            return [Phone("ah", 1, True, "ah")]

        # Keep punctuation as tokens
        tokens = re.findall(r"[a-zA-Z0-9']+|[\,\.\!\?\:\;\-]", text.lower())
        out: List[Phone] = []
        for tok in tokens:
            if re.match(r"^[a-z0-9']+$", tok):
                out.extend(self.word_to_phones(tok))
                out.append(Phone("|", None, False, "|"))
            else:
                # punctuation -> pause
                out.append(Phone("sil", None, False, tok))
        # trim trailing boundary
        while out and out[-1].sym in {"|"}:
            out.pop()
        return out or [Phone("ah", 1, True, text)]
EOF