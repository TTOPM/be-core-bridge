cat > BELEL-VIVOX-FORGE/vivox_linguistic_engine.py << 'EOF'
# BELEL-VIVOX LINGUISTIC ENGINE v1.0
# Sovereign offline planner: Lyrics -> Phonemes -> Prosody -> Forge-ready phoneme_sequence
# Zero external runtime services. CMUdict optional (local file).
# Designed to feed VivoxForgeCore.sing() without touching your organ physics.

from __future__ import annotations
import os
import re
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

# -----------------------------
# Config + phone inventory
# -----------------------------

@dataclass(frozen=True)
class LinguisticConfig:
    cmudict_path: str = "BELEL-VIVOX-FORGE/assets/cmudict.txt"
    use_cmudict: bool = True
    fallback_rules: bool = True

    # timing (ms) - tuned for intelligibility; your organ handles realism
    vowel_ms_stressed: int = 150
    vowel_ms_unstressed: int = 105
    consonant_ms_default: int = 55
    stop_ms: int = 55
    fricative_ms: int = 75
    nasal_ms: int = 65
    liquid_ms: int = 55

    # punctuation pauses (ms)
    pause_short: int = 80
    pause_long: int = 140

    # pitch
    base_f0_hz: float = 220.0
    f0_min_hz: float = 70.0
    f0_max_hz: float = 880.0

    # word boundary micro-gap: encoded as tiny "sil" slices
    boundary_sil_ms: int = 16

# Vivox internal vowel symbols (include "ee" alias if you keep it in your organ mapping)
VOWELS = {"iy","ih","ee","eh","ae","aa","ah","ao","ow","oh","uh","uw","er"}

# Minimal consonants expected by your core formant logic + bursts
STOPS = {"p","b","t","d","k","g","ch","jh"}
FRICATIVES = {"s","z","sh","zh","f","v","th","dh","h"}
NASALS = {"m","n","ng"}
LIQUIDS = {"r","l","y","w"}

# Tokenization: words + punctuation
TOKEN_RE = re.compile(r"[A-Za-z0-9']+|[\,\.\!\?\:\;\-]")

# CMUdict format: WORD  PH1 PH2 ...
CMUDICT_RE = re.compile(r"^([A-Z0-9']+)(\(\d+\))?\s+(.+)$")
ARPABET_STRESS_RE = re.compile(r"(\D+)([012])$")

ARPABET_TO_VIVOX: Dict[str, str] = {
    # vowels
    "IY":"iy","IH":"ih","EH":"eh","AE":"ae","AA":"aa","AH":"ah","AO":"ao","OW":"ow","UH":"uh","UW":"uw","ER":"er",
    "EY":"eh","AY":"ah","AW":"ow","OY":"ao",
    "AX":"ah","AXR":"er","IX":"ih","UX":"uh",
    # consonants
    "P":"p","B":"b","T":"t","D":"d","K":"k","G":"g","CH":"ch","JH":"jh",
    "M":"m","N":"n","NG":"ng",
    "F":"f","V":"v","S":"s","Z":"z","SH":"sh","ZH":"zh","TH":"th","DH":"dh","HH":"h",
    "R":"r","L":"l","Y":"y","W":"w",
}

@dataclass
class Phone:
    sym: str
    stress: Optional[int]  # 0/1/2 for vowels
    raw: str

    @property
    def is_vowel(self) -> bool:
        return self.sym in VOWELS

# -----------------------------
# Utilities
# -----------------------------

def _clamp(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))

def _strip_stress(tok: str) -> Tuple[str, Optional[int]]:
    tok = tok.strip()
    m = ARPABET_STRESS_RE.match(tok)
    if m:
        return m.group(1), int(m.group(2))
    return tok, None

def _norm_space(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())

def _note_to_hz(note: str) -> Optional[float]:
    # C4, D#3, Bb5
    note = (note or "").strip()
    m = re.match(r"^([A-Ga-g])([#b]?)(-?\d+)$", note)
    if not m:
        return None
    letter = m.group(1).upper()
    accidental = m.group(2)
    octave = int(m.group(3))
    idx = {"C":0,"D":2,"E":4,"F":5,"G":7,"A":9,"B":11}.get(letter)
    if idx is None:
        return None
    if accidental == "#":
        idx += 1
    elif accidental == "b":
        idx -= 1
    midi = (octave + 1) * 12 + idx
    return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))

def _parse_melody(melody: str) -> List[Tuple[float, float]]:
    """
    "C4:1 D4:1 E4:2" -> [(hz, beats), ...]
    """
    melody = (melody or "").strip()
    if not melody:
        return []
    out: List[Tuple[float, float]] = []
    for part in melody.split():
        if ":" not in part:
            continue
        n, b = part.split(":", 1)
        hz = _note_to_hz(n)
        if hz is None:
            continue
        try:
            beats = float(b)
        except Exception:
            beats = 1.0
        beats = _clamp(beats, 0.10, 32.0)
        out.append((float(hz), float(beats)))
    return out

def _expand_melody_targets(events: Sequence[Tuple[float, float]], total_ms: int, bpm: float) -> List[float]:
    if not events:
        return []
    beat_ms = 60000.0 / max(30.0, float(bpm))
    total_beats = sum(b for _, b in events)
    if total_beats <= 0:
        return []
    scale = total_ms / (total_beats * beat_ms)
    targets: List[float] = []
    for hz, beats in events:
        reps = max(1, int(round(beats * scale)))
        targets.extend([float(hz)] * reps)
    return targets

# -----------------------------
# CMUdict loader (offline)
# -----------------------------

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
        alts = self.lex.get((word or "").lower().strip())
        if not alts:
            return None
        return alts[0]  # stable first variant

# -----------------------------
# Fallback G2P (minimal, safe)
# -----------------------------

def _fallback_g2p(word: str) -> List[Phone]:
    w = (word or "").lower()
    out: List[Phone] = []
    i = 0
    while i < len(w):
        if w[i:i+2] == "th":
            out.append(Phone("th", None, "th")); i += 2; continue
        if w[i:i+2] == "sh":
            out.append(Phone("sh", None, "sh")); i += 2; continue
        if w[i:i+2] == "ch":
            out.append(Phone("ch", None, "ch")); i += 2; continue
        if w[i:i+2] == "ng":
            out.append(Phone("ng", None, "ng")); i += 2; continue

        ch = w[i]
        if ch in "aeiou":
            sym = {"a":"ah","e":"eh","i":"ih","o":"ow","u":"uh"}[ch]
            out.append(Phone(sym, 1, ch))
            i += 1
            continue

        m = {
            "p":"p","b":"b","t":"t","d":"d","k":"k","g":"g",
            "m":"m","n":"n","f":"f","v":"v","s":"s","z":"z","h":"h",
            "r":"r","l":"l","y":"y","w":"w",
            "j":"jh","c":"k","q":"k","x":"s",
        }.get(ch)
        if m:
            out.append(Phone(m, None, ch))
        i += 1

    return out or [Phone("ah", 1, word)]

# -----------------------------
# Linguistic Engine
# -----------------------------

class VivoxLinguisticEngine:
    def __init__(self, cfg: Optional[LinguisticConfig] = None):
        self.cfg = cfg or LinguisticConfig()
        self.cm = CMUDict(self.cfg.cmudict_path)
        if self.cfg.use_cmudict:
            self.cm.load()

    def phonemize(self, lyrics: str) -> List[Phone]:
        text = _norm_space(lyrics)
        if not text:
            return [Phone("ah", 1, "ah")]

        toks = TOKEN_RE.findall(text)
        stream: List[Phone] = []

        for tok in toks:
            if re.match(r"^[A-Za-z0-9']+$", tok):
                stream.extend(self._word_to_phones(tok))
                # boundary marker: we encode as tiny sil later (better than zero)
                stream.append(Phone("|", None, "|"))
            else:
                stream.append(Phone("sil", None, tok))

        while stream and stream[-1].sym == "|":
            stream.pop()
        return stream or [Phone("ah", 1, text)]

    def _word_to_phones(self, word: str) -> List[Phone]:
        w = (word or "").lower().strip()
        if not w:
            return []
        if self.cfg.use_cmudict:
            tokens = self.cm.lookup(w)
            if tokens:
                out: List[Phone] = []
                for t in tokens:
                    base, stress = _strip_stress(t)
                    viv = ARPABET_TO_VIVOX.get(base.upper())
                    if not viv:
                        continue
                    # keep "ee" alias if you want it; map IY->ee optionally
                    if viv == "iy":
                        viv = "iy"
                    out.append(Phone(viv, stress, t))
                if out:
                    return out
        if self.cfg.fallback_rules:
            return _fallback_g2p(w)
        return [Phone("ah", 1, w)]

    def plan_phoneme_sequence(
        self,
        lyrics: str,
        duration_ms: int,
        *,
        melody: Optional[str] = None,
        bpm: float = 92.0,
        base_f0_hz: Optional[float] = None,
        emotion_intensity: float = 0.96,
        nasal_coupling: float = 0.48,
        breath_mode: str = "mixed",
        seed: Optional[int] = None,
    ) -> List[Tuple[str, float, float]]:
        """
        Returns the tuple list your organ already uses:
            (phoneme, rel_dur, base_f0_hz)

        Notes:
        - punctuation introduces "sil" segments
        - word boundaries introduce very short "sil" micro-gaps
        - stress increases vowel duration + slightly raises f0
        - optional melody maps vowel nuclei to note targets
        """
        if seed is None:
            seed_env = os.getenv("VIVOX_SEED", "").strip()
            seed = int(seed_env) if seed_env.isdigit() else None
        if seed is not None:
            random.seed(int(seed))

        cfg = self.cfg
        dur_total = max(500, int(duration_ms))
        f0_base = float(base_f0_hz if base_f0_hz is not None else cfg.base_f0_hz)
        emotion_intensity = _clamp(float(emotion_intensity), 0.0, 1.0)
        nasal_coupling = _clamp(float(nasal_coupling), 0.0, 1.0)
        breath_mode = (breath_mode or "mixed").lower().strip()

        phones = self.phonemize(lyrics)

        # Build raw segment durations (ms)
        segs: List[Tuple[str, int, Optional[int], bool, str]] = []
        # tuple: (sym, ms, stress, is_vowel, raw)
        for p in phones:
            sym = p.sym

            if sym == "|":
                # boundary micro gap
                segs.append(("sil", cfg.boundary_sil_ms, None, False, "|"))
                continue

            if sym == "sil":
                # punctuation-aware pause
                if p.raw in {".", "!", "?"}:
                    ms = cfg.pause_long
                else:
                    ms = cfg.pause_short
                segs.append(("sil", ms, None, False, p.raw))
                continue

            if sym in VOWELS:
                if p.stress == 1:
                    ms = cfg.vowel_ms_stressed
                else:
                    ms = cfg.vowel_ms_unstressed
                segs.append((sym, ms, p.stress, True, p.raw))
                continue

            # consonants
            if sym in STOPS:
                segs.append((sym, cfg.stop_ms, None, False, p.raw)); continue
            if sym in FRICATIVES:
                segs.append((sym, cfg.fricative_ms, None, False, p.raw)); continue
            if sym in NASALS:
                segs.append((sym, cfg.nasal_ms, None, False, p.raw)); continue
            if sym in LIQUIDS:
                segs.append((sym, cfg.liquid_ms, None, False, p.raw)); continue

            segs.append((sym, cfg.consonant_ms_default, None, False, p.raw))

        if not segs:
            segs = [("ah", dur_total, 1, True, "ah")]

        # Scale durations to requested total
        sum_ms = max(1, sum(ms for _, ms, *_ in segs))
        scale = dur_total / float(sum_ms)
        segs_scaled: List[Tuple[str, int, Optional[int], bool, str]] = []
        for sym, ms, stress, isv, raw in segs:
            ms2 = max(12, int(round(ms * scale)))
            segs_scaled.append((sym, ms2, stress, isv, raw))

        # Melody targets (optional) mapped to vowel nuclei
        vowel_targets: List[float] = []
        if melody:
            events = _parse_melody(melody)
            if events:
                vowel_targets = _expand_melody_targets(events, dur_total, float(bpm))

        # Assign f0 per segment
        seq: List[Tuple[str, float, float]] = []
        vowel_i = 0
        running_f0 = f0_base

        for sym, ms, stress, isv, _raw in segs_scaled:
            if sym == "sil":
                f0 = running_f0
            else:
                if isv and vowel_targets:
                    if vowel_i < len(vowel_targets):
                        f0 = float(vowel_targets[vowel_i])
                        vowel_i += 1
                    else:
                        f0 = running_f0
                else:
                    # speech-like contour: tiny declination + stress bump
                    f0 = running_f0
                    running_f0 *= 0.9993

                if isv and stress == 1:
                    f0 *= (1.0 + 0.035 * emotion_intensity)

            f0 = _clamp(f0, cfg.f0_min_hz, cfg.f0_max_hz)

            rel = ms / float(dur_total)
            seq.append((sym, rel, f0))

        # Normalize rel_dur sum to 1.0 (forge expects relative durations)
        rel_sum = sum(r for _, r, _ in seq)
        if rel_sum <= 0:
            return [("ah", 1.0, f0_base)]
        seq = [(ph, r / rel_sum, f0) for ph, r, f0 in seq]

        # Small articulation sharpening: ensure consonants are not starved
        # (keeps intelligibility when duration_ms is short)
        seq = self._stabilize_consonant_share(seq)

        return seq

    def _stabilize_consonant_share(self, seq: List[Tuple[str, float, float]]) -> List[Tuple[str, float, float]]:
        # Enforce a minimum relative duration for certain consonants so they remain audible.
        # This prevents ultra-fast runs from smearing words.
        min_rel = 0.0045
        boosted = []
        extra = 0.0
        for ph, rel, f0 in seq:
            if ph in STOPS or ph in FRICATIVES or ph in NASALS:
                if rel < min_rel:
                    extra += (min_rel - rel)
                    rel = min_rel
            boosted.append((ph, rel, f0))

        # Renormalize
        s = sum(r for _, r, _ in boosted)
        if s <= 0:
            return boosted
        return [(ph, r / s, f0) for ph, r, f0 in boosted]
EOF