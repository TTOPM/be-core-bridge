import argparse
import json
import time
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import numpy as np

from belel_hyper_core.belel_engine import BelelHyperEngine, BelelHyperConfig, BelelHyperRequest
from belel_hyper_core.metrics.belel_audio_metrics import compute_belel_audio_metrics
from belel_hyper_core.metrics.belel_score import BelelScoreConfig, belel_auto_score
from belel_hyper_core.distill.belel_evolution_tracker import BelelEvolutionTracker


def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha1(s: str) -> str:
    return hashlib.sha1((s or "").encode("utf-8")).hexdigest()


def _load_wav_np(path: Path) -> Tuple[np.ndarray, int]:
    # Prefer soundfile; fallback to scipy
    try:
        import soundfile as sf
        x, sr = sf.read(str(path), always_2d=False)
        return np.asarray(x, dtype=np.float32), int(sr)
    except Exception:
        from scipy.io import wavfile
        sr, x = wavfile.read(str(path))
        if np.issubdtype(x.dtype, np.integer):
            mx = float(np.iinfo(x.dtype).max)
            x = x.astype(np.float32) / mx
        else:
            x = x.astype(np.float32)
        return np.asarray(x, dtype=np.float32), int(sr)


def _load_score_config(path: Optional[str]) -> BelelScoreConfig:
    cfg = BelelScoreConfig()
    if not path:
        return cfg
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"score_config not found: {p}")
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        for k, v in obj.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
    except Exception as e:
        raise SystemExit(f"Failed to parse score_config JSON: {e}")
    return cfg


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_wav_sidecar_json(
    wav_path: Path,
    *,
    steps: int,
    guidance: float,
    seed: Optional[int],
    prompt: str,
    lyrics: str,
    duration_sec: int,
    device: str,
    dtype: str,
    codec_ckpt: Optional[str],
    denoiser_ckpt: Optional[str],
    extra: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    ALWAYS write wav sidecar:
      out_dir/<stem>.json
    """
    sidecar = wav_path.with_suffix(".json")
    payload: Dict[str, Any] = {
        "utc": _utc_now(),
        "steps": int(steps),
        "guidance": float(guidance),
        "seed": None if seed is None else int(seed),
        "duration_sec": int(duration_sec),

        "prompt_hash": _sha1(prompt),
        "lyrics_hash": _sha1(lyrics) if (lyrics or "") else "",
        "prompt": str(prompt or ""),
        "lyrics": str(lyrics or ""),

        "runtime": {
            "device": str(device),
            "dtype": str(dtype),
        },
        "checkpoints": {
            "codec_ckpt": str(codec_ckpt) if codec_ckpt else "",
            "denoiser_ckpt": str(denoiser_ckpt) if denoiser_ckpt else "",
        },
    }
    if extra:
        payload["extra"] = dict(extra)

    _write_json(sidecar, payload)
    return sidecar


def _write_mel_sidecar_pt(
    out_dir: Path,
    wav_path: Path,
    mel_path_from_engine: Optional[Path],
    *,
    prompt: str,
    lyrics: str,
    meta: Dict[str, Any],
) -> Path:
    """
    ALWAYS write mel sidecar:
      out_dir/mels/<stem>.pt
    Payload:
      {"mel": tensor, "prompt": str, "lyrics": str, "meta": {...}}
    If engine already wrote a mel .pt, we load it to get the tensor, then overwrite with richer payload.
    """
    import torch

    mels_dir = out_dir / "mels"
    mels_dir.mkdir(parents=True, exist_ok=True)

    target_pt = mels_dir / wav_path.name.replace(".wav", ".pt")

    # Load mel tensor from engine mel_path (preferred), otherwise fall back to existing target.
    src_pt = mel_path_from_engine if (mel_path_from_engine and mel_path_from_engine.exists()) else None
    if src_pt is None and target_pt.exists():
        src_pt = target_pt

    if src_pt is None:
        raise SystemExit(
            "Could not locate mel tensor to write mel sidecar. "
            "Engine must output mel_path or already save out_dir/mels/*.pt."
        )

    obj = torch.load(str(src_pt), map_location="cpu")
    mel = obj["mel"] if isinstance(obj, dict) and "mel" in obj else obj

    # normalize shape to [80,T] or [1,80,T] both accepted; store as-is but typical is [1,80,T]
    if hasattr(mel, "float"):
        mel = mel.float()

    payload = {
        "mel": mel,
        "prompt": str(prompt or ""),
        "lyrics": str(lyrics or ""),
        "meta": dict(meta or {}),
    }
    torch.save(payload, str(target_pt))
    return target_pt


def main():
    ap = argparse.ArgumentParser()

    # generation inputs
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--lyrics", default="")
    ap.add_argument("--duration", type=int, default=240)

    # inference controls (ceiling enforced by engine <= 6 if your engine is locked)
    ap.add_argument("--steps", type=int, default=6, help="Benchmark ceiling: 6 or less (engine may enforce).")
    ap.add_argument("--guidance", type=float, default=6.5)
    ap.add_argument("--dtype", default="float16")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--device", default="cuda")

    # output
    ap.add_argument("--out_dir", default="outputs/belel_ultra")
    ap.add_argument("--name", default=None, help="Optional filename for wav ('.wav' appended if missing).")

    # checkpoints
    ap.add_argument("--codec_ckpt", default=None)
    ap.add_argument("--denoiser_ckpt", default=None)

    # automation (optional)
    ap.add_argument("--auto_score", action="store_true", help="Auto-score generated wav locally (air-gapped).")
    ap.add_argument("--auto_log", action="store_true", help="Auto-log scored outputs into BelelEvolutionTracker.")
    ap.add_argument("--min_score", type=float, default=7.5, help="Minimum score required to auto-log.")
    ap.add_argument("--store_breakdown", action="store_true", help="Store full scoring breakdown in tracker extra payload.")
    ap.add_argument("--score_config", default=None, help="Optional JSON file to override BelelScoreConfig.")
    ap.add_argument("--evolution_root", default="logs/belel_evolution")

    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Build config + engine ---
    cfg = BelelHyperConfig(
        device=args.device,
        dtype=args.dtype,
        steps=int(args.steps),
        guidance=float(args.guidance),
        seed=args.seed,
        out_dir=str(out_dir),
        codec_ckpt=args.codec_ckpt,
        denoiser_ckpt=args.denoiser_ckpt,
    )

    engine = BelelHyperEngine(cfg)
    engine.load_checkpoints()
    engine.to_device()

    # --- Request ---
    filename = args.name
    if filename:
        filename = filename if filename.lower().endswith(".wav") else (filename + ".wav")

    req = BelelHyperRequest(
        prompt=str(args.prompt or ""),
        lyrics=str(args.lyrics or ""),
        duration_sec=int(args.duration),
        filename=filename,
        score=None,
        steps=int(args.steps),
        guidance=float(args.guidance),
        extra=None,
    )

    out = engine.run(req)

    wav_path = Path(out["wav_path"])
    mel_path_engine = Path(out["mel_path"]) if ("mel_path" in out and out["mel_path"]) else None

    print("wav:", str(wav_path))
    if mel_path_engine:
        print("mel(engine):", str(mel_path_engine))

    # --- ALWAYS write wav sidecar JSON ---
    wav_sidecar = _write_wav_sidecar_json(
        wav_path,
        steps=int(args.steps),
        guidance=float(args.guidance),
        seed=args.seed,
        prompt=str(args.prompt or ""),
        lyrics=str(args.lyrics or ""),
        duration_sec=int(args.duration),
        device=str(args.device),
        dtype=str(args.dtype),
        codec_ckpt=args.codec_ckpt,
        denoiser_ckpt=args.denoiser_ckpt,
        extra={
            "out_dir": str(out_dir),
        },
    )
    print("wav_sidecar:", str(wav_sidecar))

    # --- ALWAYS write mel sidecar PT with prompt/lyrics/meta ---
    mel_meta: Dict[str, Any] = {
        "utc": _utc_now(),
        "steps": int(args.steps),
        "guidance": float(args.guidance),
        "seed": None if args.seed is None else int(args.seed),
        "duration_sec": int(args.duration),
        "runtime": {"device": str(args.device), "dtype": str(args.dtype)},
        "checkpoints": {
            "codec_ckpt": str(args.codec_ckpt) if args.codec_ckpt else "",
            "denoiser_ckpt": str(args.denoiser_ckpt) if args.denoiser_ckpt else "",
        },
        "wav_sidecar": str(wav_sidecar.resolve()),
        "wav_path": str(wav_path.resolve()),
    }

    mel_sidecar = _write_mel_sidecar_pt(
        out_dir,
        wav_path,
        mel_path_engine,
        prompt=str(args.prompt or ""),
        lyrics=str(args.lyrics or ""),
        meta=mel_meta,
    )
    print("mel_sidecar:", str(mel_sidecar))

    # --- Optional: auto-score + auto-log ---
    if args.auto_score or args.auto_log:
        score_cfg = _load_score_config(args.score_config)

        x, sr = _load_wav_np(wav_path)
        metrics = compute_belel_audio_metrics(x, sr)
        score10, breakdown = belel_auto_score(metrics, cfg=score_cfg)

        print("score10:", round(float(score10), 4))

        if args.auto_log:
            if float(score10) >= float(args.min_score):
                tracker = BelelEvolutionTracker(root=args.evolution_root)
                tracker.log(
                    prompt=str(args.prompt or ""),
                    lyrics=str(args.lyrics or ""),
                    wav_path=str(wav_path.resolve()),
                    mel_path=str(mel_sidecar.resolve()) if mel_sidecar.exists() else "",
                    score=float(score10),
                    steps=int(args.steps),
                    guidance=float(args.guidance),
                    extra={
                        "auto_score": True,
                        "auto_log": True,
                        "min_score": float(args.min_score),
                        "wav_sidecar": str(wav_sidecar.resolve()),
                        "mel_sidecar": str(mel_sidecar.resolve()),
                        "breakdown": breakdown if args.store_breakdown else None,
                    },
                )
                print("evolution_logged:", True)
                print("evolution_log:", str(Path(args.evolution_root) / "evolution.jsonl"))
            else:
                print("evolution_logged:", False)
                print("reason:", f"score {float(score10):.4f} < min_score {float(args.min_score):.4f}")

    # VRAM report if CUDA
    try:
        import torch
        if str(args.device).startswith("cuda") and torch.cuda.is_available():
            print("peak_vram_gb:", round(torch.cuda.max_memory_allocated() / (1024**3), 3))
    except Exception:
        pass


if __name__ == "__main__":
    main()
