cat > BELEL-VIVOX-FORGE/vivox_score.py << 'EOF'
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .vivox_utils import clamp, note_to_hz

@dataclass
class NoteEvent:
    hz: float
    beats: float

def parse_melody(melody: str) -> List[NoteEvent]:
    """
    Melody string format:
      "C4:1 D4:1 E4:2 G4:2"
    Returns list of NoteEvent(hz, beats)
    """
    melody = (melody or "").strip()
    if not melody:
        return []
    events: List[NoteEvent] = []
    for part in melody.split():
        if ":" not in part:
            continue
        note, beats_s = part.split(":", 1)
        hz = note_to_hz(note)
        if hz is None:
            continue
        try:
            beats = float(beats_s)
        except Exception:
            beats = 1.0
        beats = clamp(beats, 0.10, 16.0)
        events.append(NoteEvent(hz=hz, beats=beats))
    return events

def expand_notes_to_targets(events: Sequence[NoteEvent], total_ms: int, bpm: float) -> List[float]:
    """
    Expands note events into per-segment f0 targets (one per planned vowel nucleus).
    Used by prosody planner (simple mapping).
    """
    if not events:
        return []
    beat_ms = 60000.0 / max(30.0, float(bpm))
    total_beats = sum(e.beats for e in events)
    if total_beats <= 0:
        return []
    scale = total_ms / (total_beats * beat_ms)
    targets: List[float] = []
    for e in events:
        reps = max(1, int(round(e.beats * scale)))
        targets.extend([float(e.hz)] * reps)
    return targets
EOF