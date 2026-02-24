# BELEL-SING / hybrid_svs / inference.py
# Vivox Forge primary render entrypoint (safe, non-invasive)
# Produces a WAV using the sovereign Vivox Forge organ.
#
# Usage:
#   python3 BELEL-SING/hybrid_svs/inference.py --lyrics "In the heart..." --out out.wav
#
# This does not change training code. It only adds a working inference path.

from __future__ import annotations

import argparse
import wave
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import numpy as np

# Local client we created
from vivox_forge_client import VivoxForgeClient


def render_vivox(
    lyrics: str,
    out_wav: str = "belel_sing_vivox.wav",
    voice_id: str = "belel_prime",
    duration_ms: int = 9200,
    emotion_intensity: float = 0.95,
    nasal_coupling: float = 0.50,
    breath_mode: str = "mixed",
) -> Tuple[str, int]:
    """
    Render lyrics using Vivox Forge as primary renderer.
    Returns (output_path, sample_rate).
    """
    client = VivoxForgeClient()

    plan: Dict[str, Any] = {
        "lyrics": lyrics,
        "voice_id": voice_id,
        "duration_ms": duration_ms,
        "emotion_intensity": emotion_intensity,
        "nasal_coupling": nasal_coupling,
        "breath_mode": breath_mode,
        # Optional: if BELEL-SING generates its own phoneme_sequence later:
        # "phoneme_sequence": [...]
    }

    audio, sr = client.render(plan)

    # Safety normalize
    audio = np.asarray(audio, dtype=np.float32)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1e-12:
        audio = audio / peak * 0.90

    out_path = Path(out_wav).as_posix()
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(int(sr))
        wf.writeframes((audio * 32767.0).astype(np.int16).tobytes())

    return out_path, int(sr)


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="BELEL-SING → Vivox Forge inference")
    p.add_argument("--lyrics", type=str, required=True, help="Lyrics to render")
    p.add_argument("--out", type=str, default="belel_sing_vivox.wav", help="Output wav path")
    p.add_argument("--voice_id", type=str, default="belel_prime", help="Voice ID")
    p.add_argument("--duration_ms", type=int, default=9200, help="Duration (ms)")
    p.add_argument("--emotion", type=float, default=0.95, help="Emotion intensity")
    p.add_argument("--nasal", type=float, default=0.50, help="Nasal coupling")
    p.add_argument("--breath_mode", type=str, default="mixed", choices=["oral", "nasal", "mixed"], help="Breath mode")
    return p


if __name__ == "__main__":
    args = _build_argparser().parse_args()
    out_path, sr = render_vivox(
        lyrics=args.lyrics,
        out_wav=args.out,
        voice_id=args.voice_id,
        duration_ms=args.duration_ms,
        emotion_intensity=args.emotion,
        nasal_coupling=args.nasal,
        breath_mode=args.breath_mode,
    )
    print(f"✅ Vivox render saved: {out_path} (sr={sr})")