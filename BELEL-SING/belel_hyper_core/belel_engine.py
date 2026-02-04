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
    dtype: str = "float16"

    # benchmark ceiling
    steps: int = 6
    guidance: float = 6.5
    seed: Optional[int] = None

    # vocoder contract
    sample_rate: int = 22050
    hop_length: int = 256
    win_length: int = 1024
    mel_bins: int = 80

    # latent + conditioning
    latent_ch: int = 32
    cond_dim: int = 1024

    # outputs + checkpoints
    out_dir: str = "outputs/belel_ultra"
    codec_ckpt: Optional[str] = None
    denoiser_ckpt: Optional[str] = None


@dataclass
class BelelHyperRequest:
    prompt: str
    lyrics: str = ""
    duration_sec: int = 240

    filename: Optional[str] = None
    score: Optional[float] = None

    steps: Optional[int] = None
    guidance: Optional[float] = None
    extra: Optional[Dict[str, Any]] = None


def _torch_dtype(dtype_name: str):
    return {"float16": torch.float16, "bfloat16": torch.bfloat16}.get(dtype_name, torch.float32)


def belel_minmax_to_range(x: torch.Tensor, lo: float = -4.0, hi: float = 4.0, eps: float = 1e-8) -> torch.Tensor:
    x_min = x.amin(dim=(1, 2), keepdim=True)
    x_max = x.amax(dim=(1, 2), keepdim=True)
    x01 = (x - x_min) / (x_max - x_min + eps)
    y = x01 * (hi - lo) + lo
    return y.clamp(lo, hi)


def _load_ckpt(path: str, map_location: str = "cpu") -> dict:
    obj = torch.load(path, map_location=map_location)
    if isinstance(obj, dict) and "state_dict" in obj:
        return obj["state_dict"]
    if isinstance(obj, dict):
        return obj
    raise ValueError(f"Unsupported checkpoint format at {path}")


class BelelHyperEngine:
    def __init__(self, cfg: BelelHyperConfig):
        self.cfg = cfg

        self.codec = BelelDeepCompressor(mel_bins=cfg.mel_bins, latent_ch=cfg.latent_ch)
        self.cond = BelelConditioner(embed_dim=cfg.cond_dim)
        self.denoiser = BelelDenoiser1D(channels=cfg.latent_ch, cond_dim=cfg.cond_dim)
        self.solver = BelelLowStepSolver(self.denoiser)

        os.makedirs(cfg.out_dir, exist_ok=True)
        os.makedirs(os.path.join(cfg.out_dir, "mels"), exist_ok=True)

    def load_checkpoints(self) -> None:
        if self.cfg.codec_ckpt:
            sd = _load_ckpt(self.cfg.codec_ckpt)
            self.codec.load_state_dict(sd, strict=True)
        if self.cfg.denoiser_ckpt:
            sd = _load_ckpt(self.cfg.denoiser_ckpt)
            self.denoiser.load_state_dict(sd, strict=True)

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

        steps = int(req.steps) if req.steps is not None else int(self.cfg.steps)
        guidance = float(req.guidance) if req.guidance is not None else float(self.cfg.guidance)

        # benchmark ceiling: 6 or less
        if steps > 6:
            raise ValueError("Belel benchmark ceiling: steps must be <= 6.")

        cond = self.cond(req.prompt, req.lyrics, device=device)

        frames = max(64, int((self.cfg.sample_rate * req.duration_sec) / self.cfg.hop_length))
        latent_T = max(64, frames // 4)

        x = torch.randn(1, self.cfg.latent_ch, latent_T, device=device, dtype=dt)
        x = self.solver.generate(x, cond, steps=steps, guidance=guidance)

        mel = self.codec.decode(x.float())
        mel = belel_minmax_to_range(mel, -4.0, 4.0)
        return mel

    @torch.no_grad()
    def mel_to_waveform(self, mel: torch.Tensor) -> torch.Tensor:
        # uses your existing vocoder entrypoint
        from infer import synthesize_audio_from_mel

        wav = synthesize_audio_from_mel(mel, device=self.cfg.device)

        if isinstance(wav, torch.Tensor):
            return wav.unsqueeze(0) if wav.ndim == 1 else wav

        import numpy as np
        if isinstance(wav, np.ndarray):
            return torch.from_numpy(wav[None, :] if wav.ndim == 1 else wav)

        raise TypeError("vocoder returned unsupported type")

    def save_wav(self, wav: torch.Tensor, filename: str) -> str:
        path = os.path.join(self.cfg.out_dir, filename)
        wav_cpu = wav.detach().float().cpu()

        try:
            import soundfile as sf
            sf.write(path, wav_cpu.squeeze(0).numpy(), self.cfg.sample_rate)
        except Exception:
            from scipy.io.wavfile import write as wavwrite
            x = wav_cpu.squeeze(0).numpy()
            peak = float(abs(x).max()) if x.size else 1.0
            peak = peak if peak > 1e-8 else 1.0
            x = (x / peak * 0.98)
            wavwrite(path, self.cfg.sample_rate, (x * 32767.0).astype("int16"))

        return path

    def save_mel(self, mel: torch.Tensor, base_name: str) -> str:
        mel_path = os.path.join(self.cfg.out_dir, "mels", base_name.replace(".wav", ".pt"))
        torch.save({"mel": mel.detach().float().cpu()}, mel_path)
        return mel_path

    def run(self, req: BelelHyperRequest) -> dict:
        mel = self.generate_mel(req)
        wav = self.mel_to_waveform(mel)

        ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        base = req.filename or f"belel_ultra_{ts}.wav"
        if not base.lower().endswith(".wav"):
            base += ".wav"

        wav_path = self.save_wav(wav, base)
        mel_path = self.save_mel(mel, base)

        # evolution logging if a score is provided
        if req.score is not None:
            from belel_hyper_core.distill.belel_evolution_tracker import BelelEvolutionTracker
            steps = int(req.steps) if req.steps is not None else int(self.cfg.steps)
            guidance = float(req.guidance) if req.guidance is not None else float(self.cfg.guidance)
            BelelEvolutionTracker().log(
                prompt=req.prompt,
                lyrics=req.lyrics,
                wav_path=wav_path,
                mel_path=mel_path,
                score=float(req.score),
                steps=steps,
                guidance=guidance,
                extra=req.extra,
            )

        return {"mel": mel, "wav": wav, "wav_path": wav_path, "mel_path": mel_path}
