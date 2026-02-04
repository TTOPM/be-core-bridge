# BELEL-SING/belel-sing-gen/belel_perf_claim_runner.py
from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List

import torch


# ============================================================
# Helpers
# ============================================================

def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _now_tag() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.gmtime())


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _find_latest_benchmark_summary(root: Path) -> Optional[Path]:
    if not root.exists():
        return None
    # newest folder first
    dirs = sorted([p for p in root.iterdir() if p.is_dir()], key=lambda p: p.name, reverse=True)
    for d in dirs:
        summ = d / "benchmark_summary.json"
        if summ.exists():
            return summ
    return None


def _torch_env_snapshot() -> Dict[str, Any]:
    snap: Dict[str, Any] = {
        "utc": _utc(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "torch": getattr(torch, "__version__", ""),
        "cuda_available": bool(torch.cuda.is_available()),
        "cuda": getattr(torch.version, "cuda", "") if hasattr(torch, "version") else "",
        "cudnn": torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else "",
    }
    if torch.cuda.is_available():
        try:
            snap["gpu_name"] = torch.cuda.get_device_name(0)
            prop = torch.cuda.get_device_properties(0)
            snap["gpu_total_vram_gb"] = float(prop.total_memory / (1024 ** 3))
        except Exception:
            pass
    return snap


def _git_snapshot() -> Dict[str, Any]:
    """
    Best-effort git metadata. Does not fail the run if git is unavailable.
    """
    def run(cmd: List[str]) -> str:
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8", "ignore").strip()
            return out
        except Exception:
            return ""

    return {
        "git_commit": run(["git", "rev-parse", "HEAD"]),
        "git_branch": run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "git_dirty": bool(run(["git", "status", "--porcelain"])),
        "git_remote": run(["git", "config", "--get", "remote.origin.url"]),
    }


def _checkpoint_hashes(codec_ckpt: str, denoiser_ckpt: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if codec_ckpt and Path(codec_ckpt).exists():
        out["codec_ckpt"] = str(codec_ckpt)
        out["codec_sha256"] = _sha256_file(codec_ckpt)
    else:
        out["codec_ckpt"] = str(codec_ckpt or "")
        out["codec_sha256"] = ""
    if denoiser_ckpt and Path(denoiser_ckpt).exists():
        out["denoiser_ckpt"] = str(denoiser_ckpt)
        out["denoiser_sha256"] = _sha256_file(denoiser_ckpt)
    else:
        out["denoiser_ckpt"] = str(denoiser_ckpt or "")
        out["denoiser_sha256"] = ""
    return out


def _parse_benchmark_results(summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts a stable performance + quality claim payload from your benchmark_summary.json.
    """
    results = summary.get("results", {}) if isinstance(summary, dict) else {}
    best: Dict[str, Any] = {"best_steps": None, "best_key": None, "best": {}}

    # Prefer 2-step for "end-to-end performance" claim; fallback to best avg time.
    if "2" in results:
        best["best_steps"] = 2
        best["best_key"] = "2"
        best["best"] = results["2"]
        return best

    # Otherwise select minimal avg time
    best_avg = None
    for k, v in results.items():
        try:
            avg = float(v.get("time_sec", {}).get("avg", 1e9))
        except Exception:
            avg = 1e9
        if best_avg is None or avg < best_avg:
            best_avg = avg
            best["best_steps"] = int(v.get("steps", int(k)))
            best["best_key"] = str(k)
            best["best"] = v

    return best


def _format_claim_sentence(*, duration_sec: int, best_steps: int, avg_time: float, p50: float, p90: float, gpu: str) -> str:
    # “Publicly stated end-to-end performance claim”
    return (
        f"BELEL Ultra2 generated {duration_sec}s audio in avg {avg_time:.2f}s "
        f"(p50 {p50:.2f}s, p90 {p90:.2f}s) at {best_steps} steps on {gpu}."
    )


# ============================================================
# Main
# ============================================================

def main():
    ap = argparse.ArgumentParser()

    # --- claim run parameters (locked defaults are “industry-leading”)
    ap.add_argument("--prompt", default="A clean, modern, radio-ready pop hook with tight drums and clear vocal presence.")
    ap.add_argument("--lyrics", default="")
    ap.add_argument("--duration", type=int, default=240, help="Seconds of audio to generate for the claim")
    ap.add_argument("--steps", default="2", help="Claim steps list, default '2' (Ultra2)")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--warmup", type=int, default=1)

    # --- engine config
    ap.add_argument("--device", default=os.environ.get("BELEL_DEVICE", "cuda"))
    ap.add_argument("--dtype", default=os.environ.get("BELEL_DTYPE", "float16"))
    ap.add_argument("--guidance", type=float, default=float(os.environ.get("BELEL_GUIDANCE", "6.0")))
    ap.add_argument("--seed", type=int, default=None)

    # --- checkpoints (prefer env, allow flags)
    ap.add_argument("--codec_ckpt", default=os.environ.get("BELEL_CODEC_CKPT", ""))
    ap.add_argument("--denoiser_ckpt", default=os.environ.get("BELEL_DENOISER_CKPT", ""))

    # --- output
    ap.add_argument("--out_dir", default="benchmarks/belel_claims")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--keep_outputs", action="store_true", help="Keep wav/mel outputs for the claim run")
    ap.add_argument("--no_benchmark_run", action="store_true", help="Only build a claim artifact from latest benchmark summary")

    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    _ensure_dir(out_dir)

    tag = args.tag or _now_tag()
    run_dir = out_dir / tag
    _ensure_dir(run_dir)

    # --------------------------------------------------------
    # Preflight
    # --------------------------------------------------------
    if not args.no_benchmark_run:
        if not args.codec_ckpt or not Path(args.codec_ckpt).exists():
            raise FileNotFoundError(f"--codec_ckpt not found: {args.codec_ckpt}")
        if not args.denoiser_ckpt or not Path(args.denoiser_ckpt).exists():
            raise FileNotFoundError(f"--denoiser_ckpt not found: {args.denoiser_ckpt}")

    env = _torch_env_snapshot()
    git = _git_snapshot()
    ckpts = _checkpoint_hashes(args.codec_ckpt, args.denoiser_ckpt)

    # --------------------------------------------------------
    # Run benchmark (claim run)
    # --------------------------------------------------------
    bench_root = run_dir / "bench"
    _ensure_dir(bench_root)

    bench_summary_path: Optional[Path] = None

    if not args.no_benchmark_run:
        # We run your existing benchmark script as a subprocess to avoid import path issues.
        # This produces: benchmarks/belel_ultra/<tag>/benchmark_summary.json
        # But we want it inside claim folder, so we set --out_dir to our run folder.
        cmd = [
            sys.executable,
            str(Path(__file__).resolve().parent / "belel_benchmark_ultra.py"),
            "--prompt", str(args.prompt),
            "--lyrics", str(args.lyrics),
            "--duration", str(int(args.duration)),
            "--steps", str(args.steps),
            "--runs", str(int(args.runs)),
            "--warmup", str(int(args.warmup)),
            "--device", str(args.device),
            "--dtype", str(args.dtype),
            "--guidance", str(float(args.guidance)),
            "--codec_ckpt", str(args.codec_ckpt),
            "--denoiser_ckpt", str(args.denoiser_ckpt),
            "--out_dir", str(bench_root),
            "--tag", "claim_bench",
        ]
        if args.keep_outputs:
            cmd.append("--save_outputs")

        t0 = time.perf_counter()
        proc = subprocess.run(cmd, capture_output=True, text=True)
        t1 = time.perf_counter()

        bench_run_elapsed = float(t1 - t0)

        # Store logs
        (run_dir / "benchmark_stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
        (run_dir / "benchmark_stderr.txt").write_text(proc.stderr or "", encoding="utf-8")

        if proc.returncode != 0:
            raise RuntimeError(
                "Benchmark subprocess failed.\n"
                f"Return code: {proc.returncode}\n"
                f"stderr (tail): {(proc.stderr or '')[-2000:]}"
            )

        # Locate summary file
        bench_summary_path = bench_root / "claim_bench" / "benchmark_summary.json"
        if not bench_summary_path.exists():
            # fallback: find latest
            bench_summary_path = _find_latest_benchmark_summary(bench_root)

        if bench_summary_path is None or not bench_summary_path.exists():
            raise FileNotFoundError("Could not locate benchmark_summary.json after claim run.")

    else:
        # build claim from latest benchmark summary under benchmarks/belel_ultra
        bench_summary_path = _find_latest_benchmark_summary(Path("benchmarks/belel_ultra"))
        if bench_summary_path is None:
            raise FileNotFoundError("No existing benchmark summary found to build a claim from.")

    summary = _read_json(Path(bench_summary_path))

    # --------------------------------------------------------
    # Build claim artifact
    # --------------------------------------------------------
    best = _parse_benchmark_results(summary)
    best_steps = int(best.get("best_steps") or 2)
    best_block = best.get("best") or {}

    time_sec = best_block.get("time_sec", {}) if isinstance(best_block, dict) else {}
    score_10 = best_block.get("score_10", {}) if isinstance(best_block, dict) else {}
    pass_rate = float(best_block.get("pass_rate", 0.0)) if isinstance(best_block, dict) else 0.0

    avg_time = float(time_sec.get("avg", 0.0) or 0.0)
    p50 = float(time_sec.get("p50", 0.0) or 0.0)
    p90 = float(time_sec.get("p90", 0.0) or 0.0)

    avg_score = float(score_10.get("avg", 0.0) or 0.0) if isinstance(score_10, dict) else 0.0

    gpu_name = str(env.get("gpu_name", "") or ("cuda" if env.get("cuda_available") else "cpu"))
    claim_sentence = _format_claim_sentence(
        duration_sec=int(args.duration),
        best_steps=int(best_steps),
        avg_time=float(avg_time),
        p50=float(p50),
        p90=float(p90),
        gpu=gpu_name,
    )

    claim: Dict[str, Any] = {
        "utc": _utc(),
        "tag": tag,
        "claim": {
            "sentence": claim_sentence,
            "duration_sec": int(args.duration),
            "steps": int(best_steps),
            "guidance": float(args.guidance),
            "dtype": str(args.dtype),
            "device": str(args.device),
            "runs": int(args.runs),
            "warmup": int(args.warmup),
            "pass_rate": float(pass_rate),
            "avg_score_10": float(avg_score),
            "timing_sec": {
                "avg": float(avg_time),
                "p50": float(p50),
                "p90": float(p90),
            },
        },
        "benchmark_summary_path": str(Path(bench_summary_path).resolve()),
        "env": env,
        "git": git,
        "checkpoints": ckpts,
        "inputs": {
            "prompt": str(args.prompt),
            "lyrics_present": bool(str(args.lyrics or "").strip()),
            "lyrics_hash": hashlib.sha1((args.lyrics or "").encode("utf-8")).hexdigest() if (args.lyrics or "").strip() else "",
            "prompt_hash": hashlib.sha1((args.prompt or "").encode("utf-8")).hexdigest(),
        },
        "publication": {
            "rule": "Publish claim only with claim.json + benchmark_summary.json + checkpoint sha256.",
            "note": "This artifact is BELEL-generated and locally verifiable.",
        },
    }

    # Attach protocol info if present
    if isinstance(summary, dict) and "protocol" in summary:
        claim["protocol"] = summary.get("protocol", {})

    # --------------------------------------------------------
    # Write claim files
    # --------------------------------------------------------
    claim_path = run_dir / "claim.json"
    _write_json(claim_path, claim)

    # Convenience copy of benchmark summary
    try:
        copy_path = run_dir / "benchmark_summary.json"
        copy_path.write_text(Path(bench_summary_path).read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass

    # Minimal public snippet
    snippet = {
        "sentence": claim_sentence,
        "pass_rate": float(pass_rate),
        "avg_score_10": float(avg_score),
        "avg_time_sec": float(avg_time),
        "p90_time_sec": float(p90),
        "gpu": gpu_name,
        "duration_sec": int(args.duration),
        "steps": int(best_steps),
    }
    _write_json(run_dir / "claim_public_snippet.json", snippet)

    print("✔ wrote:", str(claim_path))
    print("✔ wrote:", str(run_dir / "claim_public_snippet.json"))
    print("✔ benchmark_summary:", str(Path(bench_summary_path).resolve()))
    print("CLAIM:", claim_sentence)


if __name__ == "__main__":
    main()
