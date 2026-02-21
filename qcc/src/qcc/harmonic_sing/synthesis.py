from __future__ import annotations

import os
from typing import Optional

from ..constants import AUDIO_DIR


def harmonic_synthesis(text: str, ref_audio: str = "belel_harmonic.wav", out_file: str = "belel_quantum_output.wav") -> str:
    """
    HARMONIC-SING Synthesis

    Optional dependency: TTS (Coqui).
    Writes output to audio/<out_file> if available.
    """
    os.makedirs(AUDIO_DIR, exist_ok=True)
    out_path = os.path.join(AUDIO_DIR, out_file)

    try:
        from TTS.api import TTS  # type: ignore

        engine = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2")
        wav = engine.tts(text=text, speaker_wav=ref_audio)

        # Some TTS backends return numpy arrays; others bytes-like. Handle both.
        if hasattr(wav, "tobytes"):
            data = wav.tobytes()
        elif isinstance(wav, (bytes, bytearray)):
            data = bytes(wav)
        else:
            raise TypeError(f"Unexpected wav type: {type(wav)}")

        with open(out_path, "wb") as f:
            f.write(data)

        return "Synthesized under Singularity Harmony"
    except Exception as e:
        # Offline-safe: do not fail hard.
        return f"Synthesis unavailable (TTS not installed or failed): {e!r}"