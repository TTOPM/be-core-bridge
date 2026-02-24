# BELEL-SING → VIVOX FORGE PRIMARY RENDER BRIDGE
# Sovereign local renderer connector

from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np


class VivoxForgeClient:
    """
    Connects BELEL-SING orchestration layer to Vivox Forge renderer.
    This becomes the PRIMARY render engine.
    """

    def __init__(self):
        self.repo_root = self._find_repo_root()
        self.vivox_dir = self.repo_root / "BELEL-VIVOX-FORGE"

        if not self.vivox_dir.exists():
            raise RuntimeError("BELEL-VIVOX-FORGE folder not found")

        # allow import from hyphen folder
        sys.path.insert(0, str(self.vivox_dir))

        self._forge = None

    def _find_repo_root(self) -> Path:
        here = Path(__file__).resolve()
        for p in [here] + list(here.parents):
            if (p / "BELEL-VIVOX-FORGE").exists():
                return p
        raise RuntimeError("Repo root not found")

    def _lazy_init(self):
        if self._forge is not None:
            return

        import vivox_forge_core
        Forge = getattr(vivox_forge_core, "VivoxForgeCore")
        self._forge = Forge()

    def render(self, plan: Dict[str, Any]) -> Tuple[np.ndarray, int]:
        self._lazy_init()

        lyrics = str(plan.get("lyrics", "")).strip()
        if not lyrics:
            raise ValueError("Plan must contain lyrics")

        voice_id = str(plan.get("voice_id", "belel_prime"))
        duration_ms = int(plan.get("duration_ms", 9200))

        emotion_intensity = float(plan.get("emotion_intensity", 0.95))
        nasal_coupling = float(plan.get("nasal_coupling", 0.5))
        breath_mode = str(plan.get("breath_mode", "mixed"))
        phoneme_sequence = plan.get("phoneme_sequence", None)

        # call vivox forge
        audio, sr = self._forge.sing(
            lyrics=lyrics,
            voice_id=voice_id,
            duration_ms=duration_ms,
            phoneme_sequence=phoneme_sequence,
            breath_mode=breath_mode,
            nasal_coupling=nasal_coupling,
            emotion_intensity=emotion_intensity,
        )

        audio = np.asarray(audio, dtype=np.float32)
        return audio, int(sr)