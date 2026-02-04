import argparse
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

import numpy as np

from belel_hyper_core.metrics.belel_audio_metrics import compute_belel_audio_metrics
from belel_hyper_core.metrics.belel_score import BelelScoreConfig, belel_auto_score
from belel_hyper_core.distill.belel_evolution_tracker import BelelEvolutionTracker


def _load_wav(path: Path):
    # Prefer soundfile; fallback to scipy
    try:
        import soundfile as sf
        x, sr = sf.read(str(path), always_2d=False)
        return x, int(sr)
    except Exception:
        from scipy.io import wavfile
        sr, x = wavfile.read(str(path))
        # normalize int16/int32
        if np.issubdtype(x.dtype, np.integer):
            mx = float(np.iinfo(x.dtype).max)
            x = x.astype(np.float32) / mx
        else:
            x = x.astype(np.float32)
        return x, int(sr)


def _read_mel_sidecar(mel_pt: Path) -> Dict[str, Any]:
    """
    Reads mel .pt saved by engine. If it contains prompt/lyrics metadata, use them.
    Accepts:
      {"mel": tensor, "prompt": str, "lyrics": str} or {"mel": tensor}
    """
    import torch
    obj = torch.load(str(mel_pt), map_location="cpu")
    if isinstance(obj, dict):
        return {
            "prompt": str(obj.get("prompt", "") or ""),
            "lyrics": str(obj.get("lyrics", "") or ""),
        }
    return {"prompt": "", "lyrics": ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", required=True, help="Outputs directory used by BelelHyperEngine (contains wavs + mels/)")
    ap.add_argument("--min_score", type=float, default=7.5, help="Only log items >= this score")
    ap.add_argument("--steps", type=int, default=4, help="Steps used for these generations")
    ap.add_argument("--guidance", type=float, default=6.5, help="Guidance used for these generations")
    ap.add_argument("--limit", type=int, default=500, help="Max files to scan")
    ap.add_argument("--evolution_root", default="logs/belel_evolution", help="Evolution tracker root dir")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    if not out_dir.exists():
        raise SystemExit(f"out_dir not found: {out_dir}")

    wavs = sorted([p for p in out_dir.glob("*.wav")])
    wavs = wavs[: int(args.limit)]

    mels_dir = out_dir / "mels"
    tracker = BelelEvolutionTracker(root=args.evolution_root)

    cfg = BelelScoreConfig()

    kept = 0
    scanned = 0

    for wav_path in wavs:
        scanned += 1
        mel_path = mels_dir / wav_path.name.replace(".wav", ".pt")

        x, sr = _load_wav(wav_path)
        metrics = compute_belel_audio_metrics(x, sr)
        score10, breakdown = belel_auto_score(metrics, cfg=cfg)

        if score10 < float(args.min_score):
            continue

        meta = {"prompt": "", "lyrics": ""}
        if mel_path.exists():
            meta = _read_mel_sidecar(mel_path)

        tracker.log(
            prompt=meta.get("prompt", "") or "",
            lyrics=meta.get("lyrics", "") or "",
            wav_path=str(wav_path),
            mel_path=str(mel_path) if mel_path.exists() else "",
            score=float(score10),
            steps=int(args.steps),
            guidance=float(args.guidance),
            extra={"auto_score": True, "breakdown": breakdown},
        )
        kept += 1

    print("scanned_wavs:", scanned)
    print("logged_items:", kept)
    print("evolution_log:", str(Path(args.evolution_root) / "evolution.jsonl"))


if __name__ == "__main__":
    main()
