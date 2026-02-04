import argparse
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import numpy as np

from belel_hyper_core.belel_engine import BelelHyperEngine, BelelHyperConfig, BelelHyperRequest
from belel_hyper_core.metrics.belel_audio_metrics import compute_belel_audio_metrics
from belel_hyper_core.metrics.belel_score import BelelScoreConfig, belel_auto_score
from belel_hyper_core.distill.belel_evolution_tracker import BelelEvolutionTracker


def _load_wav_np(path: Path) -> Tuple[np.ndarray, int]:
    # Prefer soundfile; fallback to scipy
    try:
        import soundfile as sf
        x, sr = sf.read(str(path), always_2d=False)
        return np.asarray(x), int(sr)
    except Exception:
        from scipy.io import wavfile
        sr, x = wavfile.read(str(path))
        if np.issubdtype(x.dtype, np.integer):
            mx = float(np.iinfo(x.dtype).max)
            x = x.astype(np.float32) / mx
        else:
            x = x.astype(np.float32)
        return np.asarray(x), int(sr)


def _write_sidecar_json(
    wav_path: Path,
    *,
    steps: int,
    guidance: float,
    seed: Optional[int],
    prompt: str,
    lyrics: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Path:
    import hashlib

    sidecar = wav_path.with_suffix(".json")
    payload: Dict[str, Any] = {
        "steps": int(steps),
        "guidance": float(guidance),
        "seed": None if seed is None else int(seed),
        "prompt_hash": hashlib.sha1((prompt or "").encode("utf-8")).hexdigest(),
        "lyrics_hash": hashlib.sha1((lyrics or "").encode("utf-8")).hexdigest() if (lyrics or "") else "",
        "prompt": str(prompt or ""),
        "lyrics": str(lyrics or ""),
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if extra:
        payload["extra"] = dict(extra)

    sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return sidecar


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


def main():
    ap = argparse.ArgumentParser()

    # generation inputs
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--lyrics", default="")
    ap.add_argument("--duration", type=int, default=240)

    # core inference controls (ceiling enforced by engine <= 6)
    ap.add_argument("--steps", type=int, default=6, help="Belel benchmark ceiling: 6 or less.")
    ap.add_argument("--guidance", type=float, default=6.5)
    ap.add_argument("--dtype", default="float16")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--device", default="cuda")

    # output
    ap.add_argument("--out_dir", default="outputs/belel_ultra")
    ap.add_argument("--name", default=None)

    # checkpoints
    ap.add_argument("--codec_ckpt", default=None)
    ap.add_argument("--denoiser_ckpt", default=None)

    # provenance / automation
    ap.add_argument("--write_sidecar", action="store_true", help="Write wav .json sidecar with steps/guidance/seed + prompt/lyrics.")
    ap.add_argument("--auto_score", action="store_true", help="Auto-score generated wav locally (air-gapped).")
    ap.add_argument("--auto_log", action="store_true", help="Auto-log scored outputs into BelelEvolutionTracker.")
    ap.add_argument("--min_score", type=float, default=7.5, help="Minimum score required to auto-log (if --auto_log).")
    ap.add_argument("--store_breakdown", action="store_true", help="Store full scoring breakdown in tracker extra payload.")
    ap.add_argument("--score_config", default=None, help="Optional JSON file to override BelelScoreConfig.")

    # evolution logging root
    ap.add_argument("--evolution_root", default="logs/belel_evolution")

    args = ap.parse_args()

    # --- Build config + engine ---
    cfg = BelelHyperConfig(
        device=args.device,
        dtype=args.dtype,
        steps=int(args.steps),
        guidance=float(args.guidance),
        seed=args.seed,
        out_dir=args.out_dir,
        codec_ckpt=args.codec_ckpt,
        denoiser_ckpt=args.denoiser_ckpt,
    )

    engine = BelelHyperEngine(cfg)
    engine.load_checkpoints()
    engine.to_device()

    req = BelelHyperRequest(
        prompt=args.prompt,
        lyrics=args.lyrics,
        duration_sec=int(args.duration),
        filename=args.name,
        score=None,  # manual score no longer required
        steps=int(args.steps),
        guidance=float(args.guidance),
        extra=None,
    )

    out = engine.run(req)

    wav_path = Path(out["wav_path"])
    mel_path = Path(out["mel_path"])

    print("wav:", str(wav_path))
    print("mel:", str(mel_path))

    sidecar_path: Optional[Path] = None

    # --- Provenance: write wav sidecar ---
    if args.write_sidecar:
        sidecar_path = _write_sidecar_json(
            wav_path,
            steps=int(args.steps),
            guidance=float(args.guidance),
            seed=args.seed,
            prompt=args.prompt,
            lyrics=args.lyrics,
            extra={
                "codec_ckpt": args.codec_ckpt,
                "denoiser_ckpt": args.denoiser_ckpt,
                "duration": int(args.duration),
            },
        )
        print("sidecar:", str(sidecar_path))

    # --- Automation: score & log ---
    if args.auto_score or args.auto_log:
        score_cfg = _load_score_config(args.score_config)

        x, sr = _load_wav_np(wav_path)
        metrics = compute_belel_audio_metrics(x, sr)
        score10, breakdown = belel_auto_score(metrics, cfg=score_cfg)

        print("score10:", round(float(score10), 4))
        if args.auto_log and float(score10) >= float(args.min_score):
            tracker = BelelEvolutionTracker(root=args.evolution_root)
            tracker.log(
                prompt=str(args.prompt or ""),
                lyrics=str(args.lyrics or ""),
                wav_path=str(wav_path.resolve()),
                mel_path=str(mel_path.resolve()) if mel_path.exists() else "",
                score=float(score10),
                steps=int(args.steps),
                guidance=float(args.guidance),
                extra={
                    "auto_score": True,
                    "auto_log": True,
                    "min_score": float(args.min_score),
                    "sidecar": str(sidecar_path.resolve()) if sidecar_path and sidecar_path.exists() else "",
                    "breakdown": breakdown if args.store_breakdown else None,
                },
            )
            print("evolution_logged:", True)
            print("evolution_log:", str(Path(args.evolution_root) / "evolution.jsonl"))
        else:
            if args.auto_log:
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
