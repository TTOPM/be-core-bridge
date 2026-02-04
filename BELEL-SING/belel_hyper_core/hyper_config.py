from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class BelelHyperConfig:
    device: str = "cuda"
    dtype: str = "float16"         # "float16" | "bfloat16" | "float32"
    steps: int = 6                 # low-step generation target
    guidance: float = 6.5
    target_vram_gb: float = 3.0
    latent_channels: int = 32
    mel_bins: int = 128
    sample_rate: int = 48000
    max_duration_sec: int = 240
    seed: Optional[int] = None

    # performance toggles
    use_compile: bool = True
    use_int8_text: bool = True
    use_checkpointing: bool = True
    use_flash_attention: bool = True
