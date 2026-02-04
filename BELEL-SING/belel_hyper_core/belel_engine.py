# BELEL-SING/belel-sing-gen/belel_hyper_core/belel_engine.py
from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

import torch

from .belel_latent_codec import BelelDeepCompressor
from .belel_conditioner import BelelConditioner
from .belel_denoiser import BelelDenoiser1D
from .belel_solver import BelelLowStepSolver
from .belel_presets import BelelInferenceDefaults


# ============================================================
# Config + Request
# ============================================================

@dataclass
class BelelHyperConfig:
    # device/runtime
    device: str = "cuda"
    dtype: str = "float16"  # float16 | bfloat16 | float32
    seed: Optional[int] = None
    deterministic: bool = False  # if True: stricter determinism (can be slower)

    # inference defaults (engine-level)
    steps: int = 2
    guidance: float = 6.0
    preset: str = "ultra2"  # metadata tag only (engine will enforce ultra2 when steps==2)

    # stability controls (solver-consumed)
    clamp_pred: float = 10.0
    cfg_rescale: float = 0.7

    # performance toggles
    tf32: bool = True
    compile: bool = True

    # vocoder contract
    sample_rate: int = 22050
    hop_length: int = 256
    win_length: int = 1024
    mel_bins: int = 80

    # latent + conditioning
    latent_ch: int = 32
    cond_dim: int = 1024

    # outputs
    out_dir: str = "outputs/belel_ultra"

    # checkpoints
    codec_ckpt: Optional[str] = None
    denoiser_ckpt: Optional[str] = None

    # sidecars
    # HARD RULE: this engine ALWAYS writes mel.pt + wav.json (prompt/lyrics/meta included)
    write_sidecars: bool = True

    # optional automation (air-gapped)
    auto_score: bool = False
    auto_log: bool = False
    min_score: float = 7.5
    store_breakdown: bool = False
    evolution_root: str = "logs/belel_evolution"
    score_config_json: Optional[str] = None  # optional override JSON for score config

    # gating / enforcement knobs
    # if True: request cannot override ultra2 parameters for 2-step (recommended)
    lock_ultra2: bool = True
    # guidance safety bounds (engine-level); ultra2 may override these when locked
    guidance_min: float = 1.0
    guidance_max: float = 7.5


@dataclass
class BelelHyperRequest:
    prompt: str
    lyrics: str = ""
    duration_sec: int = 240
    filename: Optional[str] = None

    # optional overrides
    steps: Optional[int] = None
    guidance: Optional[float] = None
    seed: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None


# ============================================================
# Helpers
# ============================================================

def _torch_dtype(dtype_name: str):
    return {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }.get(str(dtype_name).lower(), torch.float32)


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha1_str(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()


def _sha1_file(path: Optional[str]) -> str:
    """
    Robust sha1 of a file on disk. Returns "" if missing.
    This is used for provenance (ckpt hashes).
    """
    if not path:
        return ""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    h = hashlib.sha1()
    try:
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def _ensure_dir(p: str) -> None:
    Path(p).mkdir(parents=True, exist_ok=True)


def _load_ckpt_state_dict(path: str) -> dict:
    obj = torch.load(path, map_location="cpu")
    if isinstance(obj, dict) and "state_dict" in obj and isinstance(obj["state_dict"], dict):
        return obj["state_dict"]
    if isinstance(obj, dict):
        return obj
    raise ValueError(f"Unsupported checkpoint format at: {path}")


def _safe_json_dump(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def belel_minmax_to_range(x: torch.Tensor, lo: float = -4.0, hi: float = 4.0, eps: float = 1e-8) -> torch.Tensor:
    """
    Min-max normalize per-sample to [lo,hi] and clamp.
    Input: [B, mel_bins, T]
    """
    x_min = x.amin(dim=(1, 2), keepdim=True)
    x_max = x.amax(dim=(1, 2), keepdim=True)
    x01 = (x - x_min) / (x_max - x_min + eps)
    y = x01 * (hi - lo) + lo
    return y.clamp(lo, hi)


def _set_determinism(enabled: bool) -> None:
    if not enabled:
        return
    try:
        torch.use_deterministic_algorithms(True)
    except Exception:
        pass
    try:
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except Exception:
        pass


def _clamp_guidance(g: float, gmin: float, gmax: float) -> float:
    try:
        gv = float(g)
    except Exception:
        gv = float(gmin)
    return float(max(float(gmin), min(float(gmax), gv)))


# ============================================================
# Engine
# ============================================================

class BelelHyperEngine:
    """
    Core guarantees:
      - If steps == 2: enforce BelelInferenceDefaults.ultra2() as the canonical preset (locked)
      - Always write:
          (1) mel sidecar .pt = {"mel": tensor, "prompt": str, "lyrics": str, "meta": {...}}
          (2) wav sidecar .json = provenance + steps/guidance/seed/ckpt hashes + hashes + utc
      - Optional: auto-score + auto-log (air-gapped)
    """

    def __init__(self, cfg: BelelHyperConfig):
        self.cfg = cfg

        # canonical ultra2 preset (locked 2-step)
        self.ultra2 = BelelInferenceDefaults.ultra2()

        # cached ckpt hashes for provenance
        self.codec_ckpt_sha1 = _sha1_file(cfg.codec_ckpt)
        self.denoiser_ckpt_sha1 = _sha1_file(cfg.denoiser_ckpt)

        # core modules
        self.codec = BelelDeepCompressor(mel_bins=cfg.mel_bins, latent_ch=cfg.latent_ch)
        self.cond = BelelConditioner(embed_dim=cfg.cond_dim)
        self.denoiser = BelelDenoiser1D(channels=cfg.latent_ch, cond_dim=cfg.cond_dim)
        self.solver = BelelLowStepSolver(self.denoiser)

        # outputs
        _ensure_dir(cfg.out_dir)
        _ensure_dir(str(Path(cfg.out_dir) / "mels"))

    # ---------- lifecycle

    def load_checkpoints(self) -> None:
        if self.cfg.codec_ckpt:
            sd = _load_ckpt_state_dict(self.cfg.codec_ckpt)
            self.codec.load_state_dict(sd, strict=True)

        if self.cfg.denoiser_ckpt:
            sd = _load_ckpt_state_dict(self.cfg.denoiser_ckpt)
            self.denoiser.load_state_dict(sd, strict=True)

    def to_device(self) -> "BelelHyperEngine":
        _set_determinism(self.cfg.deterministic)

        # tf32
        if self.cfg.tf32 and str(self.cfg.device).startswith("cuda"):
            try:
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
                torch.set_float32_matmul_precision("high")
            except Exception:
                pass

        dt = _torch_dtype(self.cfg.dtype)

        self.codec.to(self.cfg.device, dtype=dt)
        self.denoiser.to(self.cfg.device, dtype=dt)
        self.cond.to(self.cfg.device)

        # compile denoiser (best-effort)
        if self.cfg.compile:
            try:
                self.denoiser = torch.compile(self.denoiser)  # type: ignore
                self.solver.denoiser = self.denoiser
            except Exception:
                pass

        return self

    # ---------- enforcement: resolve effective inference params

    def _resolve_effective_params(self, req: BelelHyperRequest) -> Dict[str, Any]:
        """
        Produces the final effective inference parameters after applying:
          - request overrides
          - engine ceilings
          - ultra2 lock (steps==2 => enforce ultra2)
          - guidance clamping
        """
        # requested (fallback to cfg)
        steps_req = int(req.steps) if req.steps is not None else int(self.cfg.steps)
        guidance_req = float(req.guidance) if req.guidance is not None else float(self.cfg.guidance)

        if steps_req not in (2, 4, 6):
            raise ValueError("BelelHyperEngine steps must be one of: 2, 4, 6")

        # final seed: request overrides engine seed (for reproducibility)
        seed_eff: Optional[int]
        if req.seed is not None:
            seed_eff = int(req.seed)
        elif self.cfg.seed is not None:
            seed_eff = int(self.cfg.seed)
        else:
            seed_eff = None

        # lock ultra2 for steps==2
        if int(steps_req) == 2 and bool(self.cfg.lock_ultra2):
            steps_eff = 2
            guidance_eff = float(self.ultra2.guidance)
            clamp_pred_eff = float(self.ultra2.clamp_pred)
            cfg_rescale_eff = float(self.ultra2.cfg_rescale)
            preset_tag = "ultra2"
            preset_meta = self.ultra2.as_meta()
            # ultra2 lock uses its own guidance, but we still clamp to global safety
            guidance_eff = _clamp_guidance(guidance_eff, float(self.cfg.guidance_min), float(self.cfg.guidance_max))
        else:
            steps_eff = int(steps_req)
            guidance_eff = _clamp_guidance(guidance_req, float(self.cfg.guidance_min), float(self.cfg.guidance_max))
            clamp_pred_eff = float(self.cfg.clamp_pred)
            cfg_rescale_eff = float(self.cfg.cfg_rescale) if steps_eff == 2 else 0.0
            preset_tag = str(self.cfg.preset or "custom")
            preset_meta = {}

        return {
            "steps": int(steps_eff),
            "guidance": float(guidance_eff),
            "seed": None if seed_eff is None else int(seed_eff),
            "clamp_pred": float(clamp_pred_eff),
            "cfg_rescale": float(cfg_rescale_eff),
            "preset_tag": str(preset_tag),
            "preset_meta": dict(preset_meta) if isinstance(preset_meta, dict) else {},
        }

    # ---------- generation

    @torch.inference_mode()
    def generate_mel(self, req: BelelHyperRequest, eff: Dict[str, Any]) -> torch.Tensor:
        seed_eff = eff.get("seed", None)

        if seed_eff is not None:
            torch.manual_seed(int(seed_eff))
            if str(self.cfg.device).startswith("cuda") and torch.cuda.is_available():
                try:
                    torch.cuda.manual_seed_all(int(seed_eff))
                except Exception:
                    pass

        steps = int(eff["steps"])
        guidance = float(eff["guidance"])

        device = self.cfg.device
        dt = _torch_dtype(self.cfg.dtype)

        # conditioning
        cond = self.cond(req.prompt, req.lyrics, device=device)

        # latent length heuristic (consistent and deterministic)
        frames = max(64, int((self.cfg.sample_rate * int(req.duration_sec)) / self.cfg.hop_length))
        latent_T = max(64, frames // 4)

        x = torch.randn(1, int(self.cfg.latent_ch), int(latent_T), device=device, dtype=dt)

        # solver stability controls
        clamp_pred = float(eff["clamp_pred"])
        cfg_rescale = float(eff["cfg_rescale"]) if steps == 2 else 0.0

        preset = self.ultra2 if (steps == 2 and bool(self.cfg.lock_ultra2)) else None

        x = self.solver.generate(
            x,
            cond,
            steps=steps,
            guidance=guidance,
            preset=preset,
            clamp_pred=clamp_pred,
            cfg_rescale=cfg_rescale,
        )

        mel = self.codec.decode(x.float())
        mel = belel_minmax_to_range(mel, -4.0, 4.0)
        return mel

    @torch.inference_mode()
    def mel_to_waveform(self, mel: torch.Tensor) -> torch.Tensor:
        # Uses your existing entrypoint in BELEL-SING/belel-sing-gen/infer.py
        # Keep import local to avoid import-time side effects.
        from infer import synthesize_audio_from_mel

        wav = synthesize_audio_from_mel(mel, device=self.cfg.device)

        if isinstance(wav, torch.Tensor):
            return wav.unsqueeze(0) if wav.ndim == 1 else wav

        # numpy fallback
        try:
            import numpy as np
            if isinstance(wav, np.ndarray):
                return torch.from_numpy(wav[None, :] if wav.ndim == 1 else wav)
        except Exception:
            pass

        raise TypeError("vocoder returned unsupported type")

    # ---------- persistence (wav + mel + sidecars)

    def _default_name(self) -> str:
        ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        return f"belel_ultra_{ts}.wav"

    def save_wav(self, wav: torch.Tensor, filename: str) -> str:
        if not filename.lower().endswith(".wav"):
            filename += ".wav"
        path = str(Path(self.cfg.out_dir) / filename)

        wav_cpu = wav.detach().float().cpu()
        try:
            import soundfile as sf
            sf.write(path, wav_cpu.squeeze(0).numpy(), int(self.cfg.sample_rate))
        except Exception:
            from scipy.io.wavfile import write as wavwrite
            x = wav_cpu.squeeze(0).numpy()
            peak = float(abs(x).max()) if x.size else 1.0
            peak = peak if peak > 1e-8 else 1.0
            x = (x / peak * 0.98)
            wavwrite(path, int(self.cfg.sample_rate), (x * 32767.0).astype("int16"))

        return path

    def save_mel_sidecar_pt(
        self,
        mel: torch.Tensor,
        base_wav_name: str,
        *,
        prompt: str,
        lyrics: str,
        meta: Dict[str, Any],
    ) -> str:
        pt_name = base_wav_name.replace(".wav", ".pt")
        mel_path = str(Path(self.cfg.out_dir) / "mels" / pt_name)
        torch.save(
            {
                "mel": mel.detach().float().cpu(),
                "prompt": str(prompt or ""),
                "lyrics": str(lyrics or ""),
                "meta": dict(meta or {}),
            },
            mel_path,
        )
        return mel_path

    def save_wav_sidecar_json(
        self,
        wav_path: str,
        *,
        prompt: str,
        lyrics: str,
        meta: Dict[str, Any],
    ) -> str:
        wavp = Path(wav_path)
        sidecar = wavp.with_suffix(".json")

        # minimal + strict provenance at top-level; full meta preserved under "meta"
        payload: Dict[str, Any] = {
            "utc": meta.get("utc", _utc_now()),
            "preset": str(meta.get("preset", self.cfg.preset)),
            "steps": int(meta.get("steps", self.cfg.steps)),
            "guidance": float(meta.get("guidance", self.cfg.guidance)),
            "seed": meta.get("seed", None),
            "dtype": str(meta.get("dtype", self.cfg.dtype)),
            "tf32": bool(meta.get("tf32", self.cfg.tf32)),
            "compile": bool(meta.get("compile", self.cfg.compile)),
            "codec_ckpt": str(self.cfg.codec_ckpt or ""),
            "denoiser_ckpt": str(self.cfg.denoiser_ckpt or ""),
            "codec_ckpt_sha1": str(self.codec_ckpt_sha1 or ""),
            "denoiser_ckpt_sha1": str(self.denoiser_ckpt_sha1 or ""),
            "prompt_hash": _sha1_str(prompt),
            "lyrics_hash": _sha1_str(lyrics) if (lyrics or "") else "",
            "prompt": str(prompt or ""),
            "lyrics": str(lyrics or ""),
            "meta": dict(meta or {}),
        }

        _safe_json_dump(sidecar, payload)
        return str(sidecar)

    # ---------- optional automation: score + evolution log

    def _auto_score_and_log(
        self,
        *,
        wav_path: str,
        mel_path: str,
        prompt: str,
        lyrics: str,
        meta: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not (self.cfg.auto_score or self.cfg.auto_log):
            return None

        from belel_hyper_core.metrics.belel_audio_metrics import compute_belel_audio_metrics
        from belel_hyper_core.metrics.belel_score import BelelScoreConfig, belel_auto_score
        from belel_hyper_core.distill.belel_evolution_tracker import BelelEvolutionTracker

        # load wav (prefer soundfile)
        import numpy as np
        try:
            import soundfile as sf
            x, sr = sf.read(str(wav_path), always_2d=False)
            x = np.asarray(x, dtype=np.float32)
            sr = int(sr)
        except Exception:
            from scipy.io import wavfile
            sr, x = wavfile.read(str(wav_path))
            if np.issubdtype(x.dtype, np.integer):
                mx = float(np.iinfo(x.dtype).max)
                x = x.astype(np.float32) / mx
            else:
                x = x.astype(np.float32)
            sr = int(sr)

        # score config override
        cfg = BelelScoreConfig()
        if self.cfg.score_config_json:
            p = Path(self.cfg.score_config_json)
            if p.exists():
                try:
                    obj = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            if hasattr(cfg, k):
                                setattr(cfg, k, v)
                except Exception:
                    pass

        metrics = compute_belel_audio_metrics(x, sr)
        score10, breakdown = belel_auto_score(metrics, cfg=cfg)

        out: Dict[str, Any] = {
            "score10": float(score10),
            "metrics": {
                "sr": int(getattr(metrics, "sr", sr)),
                "duration_sec": float(getattr(metrics, "duration_sec", 0.0)),
            },
        }
        if self.cfg.store_breakdown:
            out["breakdown"] = breakdown

        if self.cfg.auto_log and float(score10) >= float(self.cfg.min_score):
            tracker = BelelEvolutionTracker(root=self.cfg.evolution_root)
            tracker.log(
                prompt=str(prompt or ""),
                lyrics=str(lyrics or ""),
                wav_path=str(Path(wav_path).resolve()),
                mel_path=str(Path(mel_path).resolve()) if mel_path else "",
                score=float(score10),
                steps=int(meta.get("steps", self.cfg.steps)),
                guidance=float(meta.get("guidance", self.cfg.guidance)),
                extra={
                    "auto_score": True,
                    "auto_log": True,
                    "min_score": float(self.cfg.min_score),
                    "preset": str(meta.get("preset", self.cfg.preset)),
                    "codec_ckpt_sha1": str(self.codec_ckpt_sha1 or ""),
                    "denoiser_ckpt_sha1": str(self.denoiser_ckpt_sha1 or ""),
                    **({"breakdown": breakdown} if self.cfg.store_breakdown else {}),
                },
            )
            out["evolution_logged"] = True
            out["evolution_log"] = str(Path(self.cfg.evolution_root) / "evolution.jsonl")
        else:
            out["evolution_logged"] = False

        return out

    # ---------- main run

    def run(self, req: BelelHyperRequest) -> Dict[str, Any]:
        # optional VRAM reset
        if str(self.cfg.device).startswith("cuda") and torch.cuda.is_available():
            try:
                torch.cuda.reset_peak_memory_stats()
            except Exception:
                pass

        t0 = time.time()

        # resolve effective params (includes ultra2 enforcement)
        eff = self._resolve_effective_params(req)
        steps = int(eff["steps"])
        guidance = float(eff["guidance"])

        # build meta once, reuse across sidecars
        meta: Dict[str, Any] = {
            "utc": _utc_now(),
            "preset": str(eff.get("preset_tag", self.cfg.preset or "custom")),
            "steps": int(steps),
            "guidance": float(guidance),
            "seed": eff.get("seed", None),
            "dtype": str(self.cfg.dtype),
            "tf32": bool(self.cfg.tf32),
            "compile": bool(self.cfg.compile),
            "codec_ckpt": str(self.cfg.codec_ckpt or ""),
            "denoiser_ckpt": str(self.cfg.denoiser_ckpt or ""),
            "codec_ckpt_sha1": str(self.codec_ckpt_sha1 or ""),
            "denoiser_ckpt_sha1": str(self.denoiser_ckpt_sha1 or ""),
            "clamp_pred": float(eff.get("clamp_pred", self.cfg.clamp_pred)),
            "cfg_rescale": float(eff.get("cfg_rescale", self.cfg.cfg_rescale)) if steps == 2 else 0.0,
            "guidance_bounds": {"min": float(self.cfg.guidance_min), "max": float(self.cfg.guidance_max)},
            "lock_ultra2": bool(self.cfg.lock_ultra2),
        }

        # attach locked ultra2 meta (canonical, when enforced)
        preset_meta = eff.get("preset_meta", {})
        if isinstance(preset_meta, dict) and preset_meta:
            meta.update(preset_meta)

        if req.extra and isinstance(req.extra, dict):
            meta["extra"] = dict(req.extra)

        # generate
        mel = self.generate_mel(req, eff)
        wav = self.mel_to_waveform(mel)

        # persist
        base_name = req.filename or self._default_name()
        if not base_name.lower().endswith(".wav"):
            base_name += ".wav"

        wav_path = self.save_wav(wav, base_name)

        # ALWAYS write mel sidecar .pt (prompt/lyrics/meta inside)
        mel_path = self.save_mel_sidecar_pt(
            mel,
            base_name,
            prompt=req.prompt,
            lyrics=req.lyrics,
            meta=meta,
        )

        # ALWAYS write wav sidecar .json (prompt/lyrics/meta inside)
        wav_sidecar = self.save_wav_sidecar_json(
            wav_path,
            prompt=req.prompt,
            lyrics=req.lyrics,
            meta=meta,
        )

        elapsed = time.time() - t0
        meta["elapsed_sec"] = float(elapsed)

        if str(self.cfg.device).startswith("cuda") and torch.cuda.is_available():
            try:
                meta["peak_vram_gb"] = float(torch.cuda.max_memory_allocated() / (1024 ** 3))
            except Exception:
                pass

        # optional auto-score + auto-log
        auto = self._auto_score_and_log(
            wav_path=wav_path,
            mel_path=mel_path,
            prompt=req.prompt,
            lyrics=req.lyrics,
            meta=meta,
        )

        return {
            "mel": mel,
            "wav": wav,
            "wav_path": wav_path,
            "mel_path": mel_path,
            "wav_sidecar": wav_sidecar,
            "meta": meta,
            "auto": auto,
        }
