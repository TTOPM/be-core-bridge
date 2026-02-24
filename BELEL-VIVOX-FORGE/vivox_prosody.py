cat > BELEL-VIVOX-FORGE/vivox_prosody.py << 'EOF'
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .vivox_utils import Phone, is_vowel, clamp
from .vivox_score import parse_melody, expand_notes_to_targets

@dataclass
class ProsodyConfig:
    bpm: float = 92.0
    base_f0_hz: float = 220.0
    vowel_ms_stressed: int = 140
    vowel_ms_unstressed: int = 95
    consonant_ms_default: int = 55
    fricative_ms: int = 70
    stop_ms: int = 55
    nasal_ms: int = 60
    pause_ms_short: int = 80
    pause_ms_long: int = 140

@dataclass
class PlannedSegment:
    phoneme: str
    dur_ms: int
    f0_hz: float
    energy: float
    nasal_coupling: float
    phonation_mode: str

def _dur_for_phone(p: Phone, cfg: ProsodyConfig) -> int:
    if p.sym == "sil":
        # punctuation decides later
        return cfg.pause_ms_short
    if p.sym == "|":
        return 0
    if p.is_vowel:
        if p.stress == 1:
            return cfg.vowel_ms_stressed
        return cfg.vowel_ms_unstressed
    # consonants
    if p.sym in {"s","z","sh","zh","f","v","th","dh","h"}:
        return cfg.fricative_ms
    if p.sym in {"p","b","t","d","k","g","ch","jh"}:
        return cfg.stop_ms
    if p.sym in {"m","n","ng"}:
        return cfg.nasal_ms
    return cfg.consonant_ms_default

def plan(
    phones: Sequence[Phone],
    total_ms: int,
    cfg: Optional[ProsodyConfig] = None,
    melody: Optional[str] = None,
    breath_mode: str = "mixed",
    nasal_base: float = 0.40,
    phonation_mode: str = "modal",
    emotion_intensity: float = 0.95,
) -> List[PlannedSegment]:
    """
    Converts phoneme stream -> segment plan:
      (phoneme, dur_ms, f0_hz, energy, nasal_coupling, phonation_mode)
    If melody is provided, assigns vowel nuclei to note targets.
    """
    cfg = cfg or ProsodyConfig()
    breath_mode = (breath_mode or "mixed").lower()
    phonation_mode = (phonation_mode or "modal").lower()
    nasal_base = clamp(float(nasal_base), 0.0, 1.0)
    emotion_intensity = clamp(float(emotion_intensity), 0.0, 1.0)

    # initial raw durations
    raw: List[PlannedSegment] = []
    for p in phones:
        d = _dur_for_phone(p, cfg)
        if p.sym == "sil":
            # longer pause for sentence-ending punctuation
            if p.raw in {".","!","?"}:
                d = cfg.pause_ms_long
            else:
                d = cfg.pause_ms_short
        if d <= 0:
            continue

        # nasal coupling per phone
        nc = nasal_base
        if p.sym in {"m","n","ng"}:
            nc = max(nc, 0.75)
        if breath_mode == "oral":
            nc *= 0.15
        elif breath_mode == "nasal":
            nc = max(nc, 0.65)

        # energy (simple stress proxy)
        energy = 0.95
        if p.is_vowel and p.stress == 1:
            energy = 1.05
        energy *= (0.88 + 0.22*emotion_intensity)

        raw.append(PlannedSegment(
            phoneme=p.sym,
            dur_ms=int(d),
            f0_hz=float(cfg.base_f0_hz),
            energy=float(energy),
            nasal_coupling=float(nc),
            phonation_mode=phonation_mode
        ))

    if not raw:
        return [PlannedSegment("ah", 600, cfg.base_f0_hz, 1.0, nasal_base, phonation_mode)]

    # Scale durations to total_ms
    sum_ms = max(1, sum(s.dur_ms for s in raw))
    scale = total_ms / float(sum_ms)
    for s in raw:
        s.dur_ms = max(18, int(round(s.dur_ms * scale)))

    # Melody assignment (vowels get targets)
    if melody:
        events = parse_melody(melody)
        if events:
            vowel_targets = expand_notes_to_targets(events, total_ms=total_ms, bpm=cfg.bpm)
            vi = 0
            for s in raw:
                if s.phoneme in {"sil"}:
                    continue
                if s.phoneme in {"|"}:
                    continue
                # Only assign note targets to vowels; consonants inherit previous
                if s.phoneme and s.phoneme[0] and (s.phoneme in {"iy","ih","eh","ae","aa","ah","ao","ow","uh","uw","er"}):
                    if vi < len(vowel_targets):
                        s.f0_hz = float(vowel_targets[vi])
                        vi += 1
    else:
        # speech-like contour (very light declination)
        f0 = float(cfg.base_f0_hz)
        for s in raw:
            if s.phoneme == "sil":
                continue
            if s.phoneme in {"iy","ih","eh","ae","aa","ah","ao","ow","uh","uw","er"}:
                s.f0_hz = f0
                f0 *= 0.999  # tiny declination

    # Safety clamps
    for s in raw:
        s.f0_hz = clamp(s.f0_hz, 60.0, 880.0)
        s.nasal_coupling = clamp(s.nasal_coupling, 0.0, 1.0)
        s.energy = clamp(s.energy, 0.60, 1.35)

    return raw
EOF