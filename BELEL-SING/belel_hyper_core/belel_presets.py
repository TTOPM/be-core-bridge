# BELEL-SING/belel-sing-gen/belel_hyper_core/belel_engine.py
from __future__ import annotations

import time
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

import torch

from .belel_presets import BelelInferenceDefaults
from .belel_solver import BelelLowStepSolver
from .belel_latent_codec import BelelDeepCompressor
from .belel_denoiser import BelelDenoiser1D

# Optional scoring/logging (imported lazily)
# from .metrics.belel_audio_metrics import compute_belel_audio_metrics
# from .metrics.belel_score import belel_auto_score
# from .distill.belel_evolution_tracker import BelelEvolutionTracker


def _sha1_file(path: Optional[str]) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    h = hashlib.sha1()
    with p.open("rb") as f:
        while True:
            b = f.read(8192)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class BelelHyperEngine:
    """
    Canonical BELEL generation engine.

    Laws enforced here:
      - Ultra-2 is locked when steps == 2
      - Metadata + provenance always written
      - Outputs are benchmark-grade artifacts
    """

    def __init__(
        self,
        *,
        codec_ckpt: str,
        denoiser_ckpt: str,
        out_dir: str,
        device: str = "cuda",
        seed: Optional[int] = None,
        preset: Optional[BelelInferenceDefaults] = None,
    ):
        self.device = device
        self.seed = seed

        # ---- Preset law
        self.preset = preset or BelelInferenceDefaults.ultra2()

        if int(self.preset.steps) != 2:
            raise ValueError("BelelHyperEngine currently locks Ultra-2 only (steps must be 2).")

        # ---- Determinism
        if self.seed is not None:
            torch.manual_seed(int(self.seed))
            torch.cuda.manual_seed_all(int(self.seed))

        if self.preset.tf32:
            torch.backends.cuda.matmul.allow_tf32 = True
            torch.backends.cudnn.allow_tf32 = True

        # ---- Paths
        self.out_dir = Path(out_dir)
        self.mel_dir = self.out_dir / "mels"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.mel_dir.mkdir(parents=True, exist_ok=True)

        # ---- Load codec
        self.codec = BelelDeepCompressor(mel_bins=80, latent_ch=32).to(self.device)
        self.codec.load_state_dict(torch.load(codec_ckpt, map_location="cpu"))
        self.codec.eval()

        # ---- Load denoiser
        self.denoiser = BelelDenoiser1D(channels=32, cond_dim=1024).to(self.device)
        self.denoiser.load_state_dict(torch.load(denoiser_ckpt, map_location="cpu"))
        self.denoiser.eval()

        if self.preset.compile and hasattr(torch, "compile"):
            try:
                self.denoiser = torch.compile(self.denoiser)
            except Exception:
                pass

        self.solver = BelelLowStepSolver(self.denoiser)

        # ---- Provenance
        self.codec_ckpt = codec_ckpt
        self.denoiser_ckpt = denoiser_ckpt
        self.codec_hash = _sha1_file(codec_ckpt)
        self.denoiser_hash = _sha1_file(denoiser_ckpt)

    @torch.no_grad()
    def generate(
        self,
        *,
        mel_init: torch.Tensor,
        cond: torch.Tensor,
        prompt: str,
        lyrics: str,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate mel + wav with Ultra-2 locked inference.
        """

        if mel_init.device != self.device:
            mel_init = mel_init.to(self.device)
        if cond.device != self.device:
            cond = cond.to(self.device)

        B = mel_init.shape[0]
        if B != 1:
            raise ValueError("BelelHyperEngine.generate currently supports batch=1 only.")

        # ---- Solve (2-step only)
        z = self.solver.generate(
            x=mel_init,
            cond=cond,
            steps=2,
            guidance=self.preset.guidance,
            preset=self.preset,
            clamp_pred=self.preset.clamp_pred,
            cfg_rescale=self.preset.cfg_rescale,
        )

        # ---- Decode
        wav = self.codec.decode(z)

        # ---- Filenames
        stem = name or f"belel_{int(time.time())}"
        wav_path = self.out_dir / f"{stem}.wav"
        mel_path = self.mel_dir / f"{stem}.pt"
        json_path = self.out_dir / f"{stem}.json"

        # ---- Save WAV
        import soundfile as sf
        sf.write(str(wav_path), wav[0].cpu().numpy(), samplerate=44100)

        # ---- Save MEL sidecar (PRIMARY TRUTH)
        mel_payload = {
            "mel": z[0].detach().cpu(),
            "prompt": str(prompt or ""),
            "lyrics": str(lyrics or ""),
            "meta": {
                **self.preset.as_meta(),
                "engine": "BelelHyperEngine",
                "codec_ckpt": self.codec_hash,
                "denoiser_ckpt": self.denoiser_hash,
                "seed": self.seed,
                "device": self.device,
                "utc": _utc_now(),
            },
        }
        torch.save(mel_payload, mel_path)

        # ---- Save WAV JSON sidecar (SECONDARY PROVENANCE)
        wav_meta = {
            "engine": "BelelHyperEngine",
            "preset": "ultra2",
            "steps": 2,
            "guidance": float(self.preset.guidance),
            "t_knots": [float(self.preset.t0), float(self.preset.t1)],
            "codec_ckpt": self.codec_hash,
            "denoiser_ckpt": self.denoiser_hash,
            "seed": self.seed,
            "dtype": self.preset.dtype,
            "device": self.device,
            "utc": _utc_now(),
            "prompt_hash": hashlib.sha1((prompt or "").encode()).hexdigest(),
            "lyrics_hash": hashlib.sha1((lyrics or "").encode()).hexdigest(),
        }

        json_path.write_text(json.dumps(wav_meta, indent=2), encoding="utf-8")

        return {
            "wav_path": str(wav_path),
            "mel_path": str(mel_path),
            "json_path": str(json_path),
        }
