import argparse
import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Set

import numpy as np

from belel_hyper_core.metrics.belel_audio_metrics import compute_belel_audio_metrics
from belel_hyper_core.metrics.belel_score import BelelScoreConfig, belel_auto_score
from belel_hyper_core.distill.belel_evolution_tracker import BelelEvolutionTracker


# ----------------------------
# Helpers
# ----------------------------

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _load_wav(path: Path) -> Tuple[np.ndarray, int]:
    # Prefer soundfile; fallback to scipy
    try:
        import soundfile as sf
        x, sr = sf.read(str(path), always_2d=False)
        return np.asarray(x), int(sr)
    except Exception:
        from scipy.io import wavfile
        sr, x = wavfile.read(str(path))
        # normalize int16/int32
        if np.issubdtype(x.dtype, np.integer):
            mx = float(np.iinfo(x.dtype).max)
            x = x.astype(np.float32) / mx
        else:
            x = x.astype(np.float32)
        return np.asarray(x), int(sr)


def _read_mel_sidecar(mel_pt: Path) -> Dict[str, Any]:
    """
    Reads mel .pt saved by generator.
    Accepts:
      {"mel": tensor, "prompt": str, "lyrics": str, "meta": {...}} or {"mel": tensor}
    """
    import torch
    if not mel_pt.exists():
        return {"prompt": "", "lyrics": "", "meta": {}}
    obj = torch.load(str(mel_pt), map_location="cpu")
    if isinstance(obj, dict):
        return {
            "prompt": str(obj.get("prompt", "") or ""),
            "lyrics": str(obj.get("lyrics", "") or ""),
            "meta": obj.get("meta", {}) if isinstance(obj.get("meta", {}), dict) else {},
        }
    return {"prompt": "", "lyrics": "", "meta": {}}


def _infer_steps_guidance(
    default_steps: int,
    default_guidance: float,
    mel_meta: Dict[str, Any],
    wav_meta: Optional[Dict[str, Any]],
) -> Tuple[int, float]:
    """
    Priority:
      1) wav sidecar json (same stem .json)
      2) mel sidecar meta dict (if present)
      3) CLI defaults
    """
    # wav meta
    if wav_meta:
        s = wav_meta.get("steps", None)
        g = wav_meta.get("guidance", None)
        if s is not None:
            try:
                default_steps = int(s)
            except Exception:
                pass
        if g is not None:
            try:
                default_guidance = float(g)
            except Exception:
                pass

    # mel meta
    mm = mel_meta.get("meta", {}) if isinstance(mel_meta, dict) else {}
    if isinstance(mm, dict):
        s = mm.get("steps", None)
        g = mm.get("guidance", None)
        if s is not None:
            try:
                default_steps = int(s)
            except Exception:
                pass
        if g is not None:
            try:
                default_guidance = float(g)
            except Exception:
                pass

    return int(default_steps), float(default_guidance)


def _load_scored_set(manifest_jsonl: Path) -> Set[str]:
    """
    Returns a set of wav absolute paths already processed (dedupe).
    """
    done: Set[str] = set()
    if not manifest_jsonl.exists():
        return done
    for line in manifest_jsonl.read_text(encoding="utf-8").splitlines():
        try:
            obj = json.loads(line)
            p = str(obj.get("wav_path", "") or "")
            if p:
                done.add(p)
        except Exception:
            continue
    return done


# ----------------------------
# Main
# ----------------------------

def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--out_dir", required=True, help="Directory containing wavs and a mels/ folder")
    ap.add_argument("--min_score", type=float, default=7.5, help="Only log items >= this score")
    ap.add_argument("--steps", type=int, default=4, help="Default steps tag (overridden by sidecars if present)")
    ap.add_argument("--guidance", type=float, default=6.5, help="Default guidance tag (overridden by sidecars if present)")
    ap.add_argument("--limit", type=int, default=500, help="Max wav files to scan")
    ap.add_argument("--evolution_root", default="logs/belel_evolution", help="Evolution tracker root dir")

    # output behaviour
    ap.add_argument("--manifest_name", default="score_manifest.jsonl", help="Written to out_dir/")
    ap.add_argument("--dedupe", action="store_true", help="Skip wavs already in manifest")
    ap.add_argument("--write_best_index", action="store_true", help="Write best_of.json with top N entries")
    ap.add_argument("--best_n", type=int, default=64)
    ap.add_argument("--store_breakdown", action="store_true", help="Store full breakdown in manifest+tracker (bigger files)")

    # score config override (optional)
    ap.add_argument("--score_config", default=None, help="Optional path to JSON for BelelScoreConfig override")

    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    if not out_dir.exists():
        raise SystemExit(f"out_dir not found: {out_dir}")

    mels_dir = out_dir / "mels"
    manifest_path = out_dir / str(args.manifest_name)

    # dedupe set
    already = _load_scored_set(manifest_path) if args.dedupe else set()

    # load score config overrides if provided
    cfg = BelelScoreConfig()
    if args.score_config:
        scp = Path(args.score_config)
        if not scp.exists():
            raise SystemExit(f"score_config not found: {scp}")
        try:
            obj = json.loads(scp.read_text(encoding="utf-8"))
            # shallow override only for known keys
            for k, v in obj.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
        except Exception as e:
            raise SystemExit(f"Failed to parse score_config JSON: {e}")

    tracker = BelelEvolutionTracker(root=args.evolution_root)

    wavs = sorted([p for p in out_dir.glob("*.wav")])[: int(args.limit)]

    scanned = 0
    scored = 0
    logged = 0

    best_rows: List[Dict[str, Any]] = []

    for wav_path in wavs:
        scanned += 1
        wav_abs = str(wav_path.resolve())

        if args.dedupe and wav_abs in already:
            continue

        # optional wav sidecar json (same stem)
        wav_sidecar = _read_json(wav_path.with_suffix(".json"))

        # mel sidecar
        mel_pt = mels_dir / wav_path.name.replace(".wav", ".pt")
        mel_meta = _read_mel_sidecar(mel_pt)

        # steps/guidance tagging
        steps, guidance = _infer_steps_guidance(args.steps, args.guidance, mel_meta, wav_sidecar)

        # read wav + score
        x, sr = _load_wav(wav_path)
        metrics = compute_belel_audio_metrics(x, sr)
        score10, breakdown = belel_auto_score(metrics, cfg=cfg)
        scored += 1

        row = {
            "wav_path": wav_abs,
            "mel_path": str(mel_pt.resolve()) if mel_pt.exists() else "",
            "score": float(score10),
            "steps": int(steps),
            "guidance": float(guidance),
            "sr": int(metrics.sr),
            "duration_sec": float(metrics.duration_sec),
            "prompt": mel_meta.get("prompt", "") or "",
            "lyrics": mel_meta.get("lyrics", "") or "",
        }

        if args.store_breakdown:
            row["breakdown"] = breakdown  # includes metrics + weights + components

        _append_jsonl(manifest_path, row)

        # log only if above threshold
        if float(score10) >= float(args.min_score):
            tracker.log(
                prompt=row["prompt"],
                lyrics=row["lyrics"],
                wav_path=row["wav_path"],
                mel_path=row["mel_path"],
                score=float(score10),
                steps=int(steps),
                guidance=float(guidance),
                extra={
                    "auto_score": True,
                    "engine": "belel_auto_score_and_log",
                    **({"breakdown": breakdown} if args.store_breakdown else {}),
                },
            )
            logged += 1
            best_rows.append(row)

    print("scanned_wavs:", scanned)
    print("scored_wavs:", scored)
    print("logged_items:", logged)
    print("manifest:", str(manifest_path))
    print("evolution_log:", str(Path(args.evolution_root) / "evolution.jsonl"))

    # best-of index
    if args.write_best_index and best_rows:
        best_rows = sorted(best_rows, key=lambda r: float(r["score"]), reverse=True)[: int(args.best_n)]
        best_index_path = out_dir / "best_of.json"
        best_index_path.write_text(json.dumps(best_rows, indent=2, ensure_ascii=False), encoding="utf-8")
        print("best_of:", str(best_index_path))


if __name__ == "__main__":
    main()
