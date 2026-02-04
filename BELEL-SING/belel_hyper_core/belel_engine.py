from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any
import os
import time

import torch

from .belel_latent_codec import BelelDeepCompressor
from .belel_conditioner import BelelConditioner
from .belel_denoiser import BelelDenoiser1D
from .belel_solver import BelelLowStepSolver


@dataclass
class BelelHyperConfig:
    device: str = "cuda"
    dtype: str = "float16"         # float16 | bfloat16 | float32
    steps: int = 6
    guidance: float = 6.5
    seed: Optional[int] = None

    # Mel/vocoder contract
    sample_rate: int = 22050
    hop_length: int = 256
    win_length: int = 1024
    mel_bins: int = 80

    # Latent model sizes
    latent_ch: int = 32
    cond_dim: int = 1024

    # Output
    out_dir: str = "outputs/belel_ultra"


@dataclass
class BelelHyperRequest:
    prompt: str
    lyrics: str = ""
    duration_sec: int = 240
    filename: Optional[str] = None
    score: Optional[float] = None
    extra: Optional[Dict[str, Any]] = None


def _torch_dtype(dtype_name: str):
    return {"float16": torch.float16, "bfloat16": torch.bfloat16}.get(dtype_name, torch.float32)


def belel_minmax_to_range(x: torch.Tensor, lo: float = -4.0, hi: float = 4.0, eps: float = 1e-8) -> torch.Tensor:
    """
    Min-max scale tensor to [lo, hi], per-sample.
    x: [1, M, T]
    """
    x_min = x.amin(dim=(1, 2), keepdim=True)
    x_max = x.amax(dim=(1, 2), keepdim=True)
    x01 = (x - x_min) / (x_max - x_min + eps)
    y = x01 * (hi - lo) + lo
    return y.clamp(lo, hi)


class BelelHyperEngine:
    """
    Belel end-to-end fast core:
      prompt/lyrics -> conditioning
      latent -> low-step refine
      latent -> mel decode (80-bin)
      mel -> normalize to vocoder range
      vocoder -> waveform via existing Belel-SING infer.py
    """

    def __init__(self, cfg: BelelHyperConfig):
        self.cfg = cfg

        self.codec = BelelDeepCompressor(
            mel_bins=cfg.mel_bins,
            latent_ch=cfg.latent_ch,
        )
        self.cond = BelelConditioner(embed_dim=cfg.cond_dim)
        self.denoiser = BelelDenoiser1D(channels=cfg.latent_ch, cond_dim=cfg.cond_dim)
        self.solver = BelelLowStepSolver(self.denoiser)

        os.makedirs(cfg.out_dir, exist_ok=True)

    def to_device(self):
        dt = _torch_dtype(self.cfg.dtype)
        self.codec.to(self.cfg.device, dtype=dt)
        self.denoiser.to(self.cfg.device, dtype=dt)
        self.cond.to(self.cfg.device)
        return self

    @torch.no_grad()
    def generate_mel(self, req: BelelHyperRequest) -> torch.Tensor:
        if self.cfg.seed is not None:
            torch.manual_seed(self.cfg.seed)

        device = self.cfg.device
        dt = _torch_dtype(self.cfg.dtype)

        cond = self.cond(req.prompt, req.lyrics, device=device)  # [1, D]

        # Heuristic latent length:
        # frames ~= (sr * seconds) / hop
        frames = max(64, int((self.cfg.sample_rate * req.duration_sec) / self.cfg.hop_length))
        # codec downsamples by 4 (stride 2 twice) in time dimension
        latent_T = max(64, frames // 4)

        x = torch.randn(1, self.cfg.latent_ch, latent_T, device=device, dtype=dt)
        x = self.solver.generate(x, cond, steps=self.cfg.steps, guidance=self.cfg.guidance)

        mel = self.codec.decode(x.float())         # [1, 80, frames-ish]
        mel = belel_minmax_to_range(mel, -4.0, 4.0)
        return mel

    @torch.no_grad()
    def mel_to_waveform(self, mel: torch.Tensor) -> torch.Tensor:
        """
        Calls your existing Belel-SING vocoder entrypoint.
        """
        # Import here so the engine doesn't hard-fail if someone only wants mel
        from infer import synthesize_audio_from_mel

        wav = synthesize_audio_from_mel(mel, device=self.cfg.device)
        # Expect wav shape: [T] or [1, T]. Normalize to [1, T]
        if wav.ndim == 1:
            wav = wav.unsqueeze(0)
        return wav

    def save_wav(self, wav: torch.Tensor, filename: str) -> str:
        """
        Saves wav to cfg.out_dir/filename using soundfile if installed,
        else falls back to scipy.
        """
        path = os.path.join(self.cfg.out_dir, filename)
        wav_cpu = wav.detach().float().cpu()

        try:
            import soundfile as sf
            sf.write(path, wav_cpu.squeeze(0).numpy(), self.cfg.sample_rate)
        except Exception:
            from scipy.io.wavfile import write as wavwrite
            # int16 PCM
            x = wav_cpu.squeeze(0).numpy()
            x = (x / max(1e-8, float(abs(x).max())) * 0.98)
            wavwrite(path, self.cfg.sample_rate, (x * 32767.0).astype("int16"))

        return path

    def run(self, req: BelelHyperRequest) -> dict:
        mel = self.generate_mel(req)
        wav = self.mel_to_waveform(mel)

        ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        base = req.filename or f"belel_ultra_{ts}.wav"
        if not base.lower().endswith(".wav"):
            base += ".wav"
        out_path = self.save_wav(wav, base)

        return {
            "mel": mel,
            "wav": wav,
            "path": out_path,
        }
