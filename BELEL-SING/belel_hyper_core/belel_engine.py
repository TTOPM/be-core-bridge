import argparse
import json
import hashlib
import time
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

def _sha1_bytes(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def _sha1_text(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


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


def _wav_content_hash(x: np.ndarray, sr: int) -> str:
    """
    Hash normalized float audio + sr. This dedupes even if filename changes.
    We keep it cheap: clip, float32, mono reduction if needed.
    """
    y = np.asarray(x)
    if y.ndim > 1:
        y = y.mean(axis=-1)
    y = y.astype(np.float32)
    y = np.clip(y, -1.0, 1.0)
    header = f"sr={int(sr)}|n={int(y.shape[0])}|".encode("utf-8")
    return _sha1_bytes(header + y.tobytes())


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
        meta = obj.get("meta", {})
        if not isinstance(meta, dict):
            meta = {}
        return {
            "prompt": str(obj.get("prompt", "") or ""),
            "lyrics": str(obj.get("lyrics", "") or ""),
            "meta": meta,
        }
    return {"prompt": "", "lyrics": "", "meta": {}}


def _patch_mel_meta_if_missing(mel_pt: Path, meta_patch: Dict[str, Any]) -> bool:
    """
    If mel sidecar exists and has a dict format, inject missing meta keys.
    Returns True if patched.
    """
    import torch
    if not mel_pt.exists():
        return False
    obj = torch.load(str(mel_pt), map_location="cpu")
    if not isinstance(obj, dict):
        return False

    meta = obj.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}

    changed = False
    for k, v in meta_patch.items():
        if k not in meta:
            meta[k] = v
            changed = True

    if changed:
        obj["meta"] = meta
        torch.save(obj, str(mel_pt))
    return changed


def _infer_steps_guidance_seed(
    default_steps: int,
    default_guidance: float,
    default_seed: Optional[int],
    mel_meta: Dict[str, Any],
    wav_meta: Optional[Dict[str, Any]],
) -> Tuple[int, float, Optional[int]]:
    """
    Priority:
      1) wav sidecar json (same stem .json)
      2) mel sidecar meta dict (if present)
      3) CLI defaults
    """
    steps = int(default_steps)
    guidance = float(default_guidance)
    seed = default_seed

    # wav meta first
    if wav_meta:
        if "steps" in wav_meta:
            try:
                steps = int(wav_meta["steps"])
            except Exception:
                pass
        if "guidance" in wav_meta:
            try:
                guidance = float(wav_meta["guidance"])
            except Exception:
                pass
        if "seed" in wav_meta:
            try:
                seed = None if wav_meta["seed"] is None else int(wav_meta["seed"])
            except Exception:
                pass

    # mel meta next
    mm = mel_meta.get("meta", {}) if isinstance(mel_meta, dict) else {}
    if isinstance(mm, dict):
        if "steps" in mm and (wav_meta is None or "steps" not in wav_meta):
            try:
                steps = int(mm["steps"])
            except Exception:
                pass
        if "guidance" in mm and (wav_meta is None or "guidance" not in wav_meta):
            try:
                guidance = float(mm["guidance"])
            except Exception:
                pass
        if "seed" in mm and (wav_meta is None or "seed" not in wav_meta):
            try:
                seed = None if mm["seed"] is None else int(mm["seed"])
            except Exception:
                pass

    # enforce Belel ceiling
    if steps < 1 or steps > 6:
        steps = max(1, min(6, int(default_steps)))

    return int(steps), float(guidance), seed


def _ensure_wav_sidecar(
    wav_path: Path,
    *,
    steps: int,
    guidance: float,
    seed: Optional[int],
    prompt: str,
    lyrics: str,
    allow_write: bool,
) -> Optional[Path]:
    """
    Recommended upgrade: guarantee a .json sidecar exists beside every wav.
    If missing and allow_write=True, create it.
    """
    sidecar = wav_path.with_suffix(".json")
    if sidecar.exists():
        return sidecar

    if not allow_write:
        return None

    payload = {
        "steps": int(steps),
        "guidance": float(guidance),
        "seed": seed if seed is None else int(seed),
        "prompt_hash": _sha1_text(prompt or ""),
        "lyrics_hash": _sha1_text(lyrics or "") if (lyrics or "") else "",
        # keep full text locally if you want complete provenance
        "prompt": str(prompt or ""),
        "lyrics": str(lyrics or ""),
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _write_json(sidecar, payload)
    return sidecar


def _load_scored_set(manifest_jsonl: Path) -> Set[str]:
    """
    Returns a set of content hashes already processed (dedupe).
    """
    done: Set[str] = set()
    if not manifest_jsonl.exists():
        return done
    for line in manifest_jsonl.read_text(encoding="utf-8").splitlines():
        try:
            obj = json.loads(line)
            h = str(obj.get("audio_hash", "") or "")
            if h:
                done.add(h)
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
    ap.add_argument("--seed", type=int, default=None, help="Default seed tag (overridden by sidecars if present)")

    ap.add_argument("--limit", type=int, default=500, help="Max wav files to scan")
    ap.add_argument("--evolution_root", default="logs/belel_evolution", help="Evolution tracker root dir")

    # output behaviour
    ap.add_argument("--manifest_name", default="score_manifest.jsonl", help="Written to out_dir/")
    ap.add_argument("--dedupe", action="store_true", help="Skip audio already scored (hash-based)")
    ap.add_argument("--write_best_index", action="store_true", help="Write best_of.json with top N entries")
    ap.add_argument("--best_n", type=int, default=64)
    ap.add_argument("--store_breakdown", action="store_true", help="Store full breakdown in manifest+tracker (bigger files)")

    # recommended: guarantee provenance sidecars
    ap.add_argument("--ensure_sidecars", action="store_true", help="Create wav .json sidecars if missing")
    ap.add_argument("--patch_mel_meta", action="store_true", help="Inject steps/guidance/seed into mel .pt meta if missing")

    # score config override (optional)
    ap.add_argument("--score_config", default=None, help="Optional path to JSON for BelelScoreConfig override")

    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    if not out_dir.exists():
        raise SystemExit(f"out_dir not found: {out_dir}")

    mels_dir = out_dir / "mels"
    manifest_path = out_dir / str(args.manifest_name)

    # dedupe set (hash-based)
    already_hashes = _load_scored_set(manifest_path) if args.dedupe else set()

    # load score config overrides if provided
    cfg = BelelScoreConfig()
    if args.score_config:
        scp = Path(args.score_config)
        if not scp.exists():
            raise SystemExit(f"score_config not found: {scp}")
        try:
            obj = json.loads(scp.read_text(encoding="utf-8"))
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
    skipped = 0
    patched_mels = 0
    created_sidecars = 0

    best_rows: List[Dict[str, Any]] = []

    for wav_path in wavs:
        scanned += 1

        # optional wav sidecar json (same stem)
        wav_sidecar_path = wav_path.with_suffix(".json")
        wav_sidecar = _read_json(wav_sidecar_path)

        # mel sidecar
        mel_pt = mels_dir / wav_path.name.replace(".wav", ".pt")
        mel_meta = _read_mel_sidecar(mel_pt)

        # infer tags
        steps, guidance, seed = _infer_steps_guidance_seed(
            args.steps, args.guidance, args.seed, mel_meta, wav_sidecar
        )

        # recommended: ensure wav sidecar exists (writes if missing)
        sidecar_created = False
        if args.ensure_sidecars and (wav_sidecar is None):
            sc = _ensure_wav_sidecar(
                wav_path,
                steps=steps,
                guidance=guidance,
                seed=seed,
                prompt=mel_meta.get("prompt", "") or "",
                lyrics=mel_meta.get("lyrics", "") or "",
                allow_write=True,
            )
            if sc is not None and sc.exists():
                sidecar_created = True
                created_sidecars += 1

        # recommended: patch mel meta with steps/guidance/seed (if missing)
        if args.patch_mel_meta and mel_pt.exists():
            changed = _patch_mel_meta_if_missing(
                mel_pt,
                {"steps": int(steps), "guidance": float(guidance), "seed": seed},
            )
            if changed:
                patched_mels += 1
                # refresh mel_meta after patch
                mel_meta = _read_mel_sidecar(mel_pt)

        # load wav -> compute content hash
        x, sr = _load_wav(wav_path)
        audio_hash = _wav_content_hash(x, sr)

        if args.dedupe and audio_hash in already_hashes:
            skipped += 1
            continue

        # score
        metrics = compute_belel_audio_metrics(x, sr)
        score10, breakdown = belel_auto_score(metrics, cfg=cfg)
        scored += 1

        wav_abs = str(wav_path.resolve())
        mel_abs = str(mel_pt.resolve()) if mel_pt.exists() else ""

        row: Dict[str, Any] = {
            "wav_path": wav_abs,
            "mel_path": mel_abs,
            "audio_hash": audio_hash,
            "score": float(score10),
            "steps": int(steps),
            "guidance": float(guidance),
            "seed": seed if seed is None else int(seed),
            "sr": int(metrics.sr),
            "duration_sec": float(metrics.duration_sec),
            "prompt": mel_meta.get("prompt", "") or "",
            "lyrics": mel_meta.get("lyrics", "") or "",
        }

        if args.store_breakdown:
            row["breakdown"] = breakdown

        _append_jsonl(manifest_path, row)
        already_hashes.add(audio_hash)

        # evolution log only above threshold
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
                    "engine": "belel_engine_scorelog",
                    "audio_hash": audio_hash,
                    "sidecar_created": bool(sidecar_created),
                    "mel_meta_patched": bool(args.patch_mel_meta and mel_pt.exists()),
                    **({"breakdown": breakdown} if args.store_breakdown else {}),
                },
            )
            logged += 1
            best_rows.append(row)

    print("scanned_wavs:", scanned)
    print("scored_wavs:", scored)
    print("skipped_deduped:", skipped)
    print("logged_items:", logged)
    print("manifest:", str(manifest_path))
    print("evolution_log:", str(Path(args.evolution_root) / "evolution.jsonl"))
    if args.ensure_sidecars:
        print("sidecars_created:", created_sidecars)
    if args.patch_mel_meta:
        print("mels_patched:", patched_mels)

    # best-of index
    if args.write_best_index and best_rows:
        best_rows = sorted(best_rows, key=lambda r: float(r["score"]), reverse=True)[: int(args.best_n)]
        best_index_path = out_dir / "best_of.json"
        best_index_path.write_text(json.dumps(best_rows, indent=2, ensure_ascii=False), encoding="utf-8")
        print("best_of:", str(best_index_path))


if __name__ == "__main__":
    main()
