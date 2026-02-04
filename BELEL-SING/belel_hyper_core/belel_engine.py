from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

import torch

from .belel_latent_codec import BelelDeepCompressor
from .belel_conditioner import BelelConditioner
from .belel_denoiser import BelelDenoiser1D
from .belel_solver import BelelLowStepSolver

@dataclass
class BelelHyperConfig:
    device: str = "cuda"
    dtype: str = "float16"  # float16 | bfloat16 | float32
    steps: int = 6
    guidance: float = 6.5
    mel_bins: int = 128
    latent_ch: int = 32
    seed: Optional[int] = None

@dataclass
class BelelHyperRequest:
    prompt: str
    lyrics: str = ""
    duration_sec: int = 240

class BelelHyperEngine:
    """
    Fully Belel engine:
    - generates compressed-latent mel
    - plug your existing Belel vocoder after mel if desired
    """
    def __init__(self, cfg: BelelHyperConfig):
        self.cfg = cfg
        self.codec = BelelDeepCompressor(mel_bins=cfg.mel_bins, latent_ch=cfg.latent_ch)
        self.cond = BelelConditioner(embed_dim=1024)
        self.denoiser = BelelDenoiser1D(channels=cfg.latent_ch, cond_dim=1024)
        self.solver = BelelLowStepSolver(self.denoiser)

    def _torch_dtype(self):
        return {"float16": torch.float16, "bfloat16": torch.bfloat16}.get(self.cfg.dtype, torch.float32)

    def to_device(self):
        dt = self._torch_dtype()
        self.codec.to(self.cfg.device, dtype=dt)
        self.denoiser.to(self.cfg.device, dtype=dt)
        # transformers stay fp32 by default unless you manage separately
        self.cond.to(self.cfg.device)
        return self

    @torch.no_grad()
    def run(self, req: BelelHyperRequest):
        if self.cfg.seed is not None:
            torch.manual_seed(self.cfg.seed)

        device = self.cfg.device
        dt = self._torch_dtype()

        cond = self.cond(req.prompt, req.lyrics, device=device)  # [1, 1024]

        # latent length heuristic: tune based on your mel hop size
        latent_T = max(64, int(req.duration_sec * 75 / 4))
        x = torch.randn(1, self.cfg.latent_ch, latent_T, device=device, dtype=dt)

        x = self.solver.generate(x, cond, steps=self.cfg.steps, guidance=self.cfg.guidance)
        mel = self.codec.decode(x.float())  # [1, mel_bins, Tmel]

        return {"mel": mel, "latent": x, "cond": cond}
