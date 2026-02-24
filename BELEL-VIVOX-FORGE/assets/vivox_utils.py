cat > BELEL-VIVOX-FORGE/vivox_utils.py << 'EOF'
from __future__ import annotations
import math
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

ARPABET_STRESS_RE = re.compile(r"(\D+)([012])$")

# Minimal internal phoneme inventory used by Vivox Forge (extendable)
# Vowels map into these canonical symbols:
VOWELS = {"iy","ih","eh","ae","aa","ah","ao","ow","uh","uw","er"}

# Consonants used by the engine (extendable)
CONSONANTS = {"p","b","t","d","k","g","m","n","ng","f","v","s","z","sh","zh","ch","jh","th","dh","h","r","l","y","w"}

# --- Note parsing ---
NOTE_INDEX = {"C":0,"C#":1,"Db":1,"D":2,"D#":3,"Eb":3,"E":4,"F":5,"F#":6,"Gb":6,"G":7,"G#":8,"Ab":8,"A":9,"A#":10,"Bb":10,"B":11}

def clamp(x: float, lo: float, hi: float) -> float:
    return float(max(lo, min(hi, x)))

def midi_to_hz(midi: float) -> float:
    return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))

def note_to_midi(note: str) -> Optional[int]:
    """
    Accepts: C4, D#3, Bb5
    Returns MIDI int or None.
    """
    note = (note or "").strip()
    if not note:
        return None
    m = re.match(r"^([A-Ga-g])([#b]?)(-?\d+)$", note)
    if not m:
        return None
    letter = m.group(1).upper()
    accidental = m.group(2)
    octave = int(m.group(3))
    key = f"{letter}{accidental}"
    if key not in NOTE_INDEX:
        return None
    sem = NOTE_INDEX[key]
    return int((octave + 1) * 12 + sem)

def note_to_hz(note: str) -> Optional[float]:
    m = note_to_midi(note)
    return None if m is None else midi_to_hz(m)

# --- ARPABET mapping (CMUdict) -> Vivox internal phones ---
# This is intentionally conservative; you can refine later without breaking API.
ARPABET_TO_VIVOX: Dict[str, str] = {
    # Vowels
    "IY":"iy","IH":"ih","EH":"eh","AE":"ae","AA":"aa","AH":"ah","AO":"ao","OW":"ow","UH":"uh","UW":"uw","ER":"er",
    "EY":"eh","AY":"ah","AW":"ow","OY":"ao",
    "AX":"ah","AXR":"er","IX":"ih","UX":"uh",

    # Stops
    "P":"p","B":"b","T":"t","D":"d","K":"k","G":"g",

    # Nasals
    "M":"m","N":"n","NG":"ng",

    # Fricatives
    "F":"f","V":"v","S":"s","Z":"z","SH":"sh","ZH":"zh","TH":"th","DH":"dh","HH":"h",

    # Affricates
    "CH":"ch","JH":"jh",

    # Liquids/Glides
    "R":"r","L":"l","Y":"y","W":"w",

    # Silence / boundaries (internal)
    "SIL":"sil",
}

def strip_arpabet_stress(token: str) -> Tuple[str, Optional[int]]:
    """
    "AH0" -> ("AH", 0)
    "IY1" -> ("IY", 1)
    "S"   -> ("S", None)
    """
    token = token.strip()
    m = ARPABET_STRESS_RE.match(token)
    if m:
        return m.group(1), int(m.group(2))
    return token, None

@dataclass
class Phone:
    sym: str                 # vivox symbol or "sil" or "|"
    stress: Optional[int]    # 0,1,2 for vowels if known
    is_vowel: bool
    raw: str                 # original token/source

def is_vowel(sym: str) -> bool:
    return sym in VOWELS

def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())

def split_words(text: str) -> List[str]:
    text = normalize_whitespace(text.lower())
    # keep apostrophes within words, remove other punctuation into separators
    text = re.sub(r"[^a-z0-9'\s\.\,\!\?\:\;\-]", " ", text)
    return [w for w in re.split(r"\s+", text) if w]

def is_pause_token(tok: str) -> bool:
    return tok in {".", ",", "!", "?", ":", ";", "-"}
EOF