# BELEL-SING/belel-sing-gen/belel_perf_claim_runner.py
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import time
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import torch

from belel_hyper_core.belel_engine import (
    BelelHyperEngine,
    BelelHyperConfig,
    BelelHyperRequest,
)

from belel_hyper_core.metrics.belel_benchmark_protocol import (
    BelelBenchmarkProtocol,
    BelelBenchmarkGates,
    BelelBenchmarkWeights,
)


# ============================================================
# Utilities
# ============================================================

def _utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _now_utc_tag() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.gmtime())


def _ensure_dir(p: str) -> None:
    Path(p).mkdir(parents=True, exist_ok=True)


def _write_json(path: str, obj: Dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_text(path: str, s: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(s, encoding="utf-8")


def _cuda_sync(device: str) -> None:
    if str(device).startswith("cuda") and torch.cuda.is_available():
        torch.cuda.synchronize()


def _reset_peak_vram(device: str) -> None:
    if str(device).startswith("cuda") and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()


def _peak_vram_gb(device: str) -> float:
    if str(device).startswith("cuda") and torch.cuda.is_available():
        return float(torch.cuda.max_memory_allocated() / (1024 ** 3))
    return 0.0


def _sha256_file(path: str) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _try_git_rev() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        return out.decode("utf-8").strip()
    except Exception:
        return ""


def _try_git_dirty() -> bool:
    try:
        out = subprocess.check_output(["git", "status", "--porcelain"], stderr=subprocess.DEVNULL)
        return bool(out.decode("utf-8").strip())
    except Exception:
        return False


def _device_fingerprint(device: str) -> Dict[str, Any]:
    fp: Dict[str, Any] = {
        "device": str(device),
        "torch_version": torch.__version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "utc": _utc_now(),
    }

    # CUDA facts
    fp["cuda_available"] = bool(torch.cuda.is_available())
    fp["cuda_version"] = str(torch.version.cuda) if torch.version.cuda else ""
    fp["cudnn_version"] = int(torch.backends.cudnn.version()) if torch.backends.cudnn.is_available() else 0

    if str(device).startswith("cuda") and torch.cuda.is_available():
        try:
            idx = torch.cuda.current_device()
            props = torch.cuda.get_device_properties(idx)
            fp["gpu"] = {
                "name": torch.cuda.get_device_name(idx),
                "index": int(idx),
                "total_vram_gb": float(props.total_memory / (1024 ** 3)),
                "sm_count": int(props.multi_processor_count),
                "major": int(props.major),
                "minor": int(props.minor),
            }
        except Exception:
            fp["gpu"] = {"name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else ""}

    # determinism toggles (informational)
    fp["tf32_matmul_allow"] = bool(getattr(torch.backends.cuda.matmul, "allow_tf32", False)) if torch.cuda.is_available() else False
    fp["tf32_cudnn_allow"] = bool(getattr(torch.backends.cudnn, "allow_tf32", False)) if torch.backends.cudnn.is_available() else False

    fp["git_commit"] = _try_git_rev()
    fp["git_dirty"] = _try_git_dirty()

    return fp


def _stats(xs: List[float]) -> Dict[str, float]:
    if not xs:
        return {"avg": 0.0, "p50": 0.0, "p90": 0.0, "min": 0.0, "max": 0.0}
    ys = sorted(xs)
    n = len(ys)

    def q(p: float) -> float:
        i = int(round((n - 1) * p))
        i = max(0, min(n - 1, i))
        return ys[i]

    return {
        "avg": float(sum(ys) / n),
        "p50": float(q(0.50)),
        "p90": float(q(0.90)),
        "min": float(ys[0]),
        "max": float(ys[-1]),
    }


def _make_public_claim_block(claim: Dict[str, Any]) -> str:
    # Keep it assertive, reproducible, and backed by hashes + protocol gate.
    env = claim["environment"]
    run = claim["run"]
    proto = claim["protocol"]
    hw = env.get("gpu", {})
    gpu_name = hw.get("name", env.get("device", ""))
    dur = run["duration_sec"]
    steps = run["steps"]
    guidance = run["guidance"]
    n = run["runs"]

    t = claim["measured"]["time_sec"]
    v = claim["measured"]["peak_vram_gb"]
    s = claim["measured"]["score_10"]
    pass_rate = claim["measured"]["pass_rate"]

    ck = claim["checkpoints"]
    den = ck.get("denoiser_ckpt", {})
    cod = ck.get("codec_ckpt", {})

    lines = []
    lines.append("# BELEL-SING — End-to-End Performance Claim (Reproducible)\n")
    lines.append(f"- UTC: {claim.get('utc','')}")
    lines.append(f"- GPU: {gpu_name}")
    lines.append(f"- Torch: {env.get('torch_version','')} | CUDA: {env.get('cuda_version','')}")
    if env.get("git_commit"):
        lines.append(f"- Git: {env.get('git_commit')} (dirty={env.get('git_dirty')})")
    lines.append("")
    lines.append("## Claim")
    lines.append(
        f"Generated **{dur}s** of audio end-to-end in **{t['avg']:.3f}s avg** "
        f"(p50={t['p50']:.3f}s, p90={t['p90']:.3f}s) at **{steps} steps** and guidance={guidance:.2f} "
        f"over **{n} measured runs**."
    )
    lines.append(
        f"Peak VRAM: **{v['avg']:.3f} GB avg** (p90={v['p90']:.3f} GB)."
    )
    lines.append(
        f"Protocol score: **{s['avg']:.2f}/10 avg** with **pass-rate={pass_rate:.2f}** "
        f"against locked BelelBenchmark gates."
    )
    lines.append("")
    lines.append("## Integrity")
    lines.append(f"- codec_ckpt: {cod.get('path','')} sha256={cod.get('sha256','')}")
    lines.append(f"- denoiser_ckpt: {den.get('path','')} sha256={den.get('sha256','')}")
    lines.append("")
    lines.append("## Protocol (locked)")
    lines.append(f"- gates: {json.dumps(proto.get('gates',{}), ensure_ascii=False)}")
    lines.append(f"- weights: {json.dumps(proto.get('weights',{}), ensure_ascii=False)}")
    lines.append("")
    lines.append("## Reproduce")
    lines.append("Run this file with the same checkpoints and prompt/lyrics. The JSON artifact contains full run metadata.")

    return "\n".join(lines) + "\n"


# ============================================================
# Main
# ============================================================

def main():
    ap = argparse.ArgumentParser()

    # Content
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--lyrics", default="")
    ap.add_argument("--duration", type=int, default=60)

    # Runtime
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dtype", default="float16")
    ap.add_argument("--guidance", type=float, default=6.0)
    ap.add_argument("--steps", type=int, default=2, choices=[2, 4, 6])
    ap.add_argument("--seed", type=int, default=1234)

    # Checkpoints
    ap.add_argument("--codec_ckpt", required=True)
    ap.add_argument("--denoiser_ckpt", required=True)

    # Measurement
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--warmup", type=int, default=2)
    ap.add_argument("--save_outputs", action="store_true")

    # Output
    ap.add_argument("--out_dir", default="benchmarks/belel_perf_claim")
    ap.add_argument("--tag", default=None)

    # Protocol config (optional overrides)
    ap.add_argument("--gates_json", default=None, help="Optional JSON override for BelelBenchmarkGates")
    ap.add_argument("--weights_json", default=None, help="Optional JSON override for BelelBenchmarkWeights")

    args = ap.parse_args()

    tag = args.tag or _now_utc_tag()
    run_root = str(Path(args.out_dir) / tag)
    _ensure_dir(run_root)

    # Environment capture
    env = _device_fingerprint(args.device)

    # Checkpoint hashing (integrity anchor)
    codec_sha = _sha256_file(args.codec_ckpt)
    denoiser_sha = _sha256_file(args.denoiser_ckpt)

    ckpts = {
        "codec_ckpt": {"path": str(Path(args.codec_ckpt).resolve()), "sha256": codec_sha},
        "denoiser_ckpt": {"path": str(Path(args.denoiser_ckpt).resolve()), "sha256": denoiser_sha},
    }

    # Build engine (end-to-end)
    cfg = BelelHyperConfig(
        device=args.device,
        dtype=args.dtype,
        steps=6,  # ceiling; actual steps set per request
        guidance=float(args.guidance),
        seed=int(args.seed),
        out_dir=str(Path(run_root) / "outputs"),
        codec_ckpt=args.codec_ckpt,
        denoiser_ckpt=args.denoiser_ckpt,
    )

    engine = BelelHyperEngine(cfg)
    engine.load_checkpoints()
    engine.to_device()

    # Protocol (authoritative judge)
    gates = BelelBenchmarkGates()
    weights = BelelBenchmarkWeights()

    # Optional overrides from JSON
    if args.gates_json:
        p = Path(args.gates_json)
        if p.exists():
            obj = json.loads(p.read_text(encoding="utf-8"))
            for k, v in obj.items():
                if hasattr(gates, k):
                    setattr(gates, k, v)

    if args.weights_json:
        p = Path(args.weights_json)
        if p.exists():
            obj = json.loads(p.read_text(encoding="utf-8"))
            for k, v in obj.items():
                if hasattr(weights, k):
                    setattr(weights, k, v)

    protocol = BelelBenchmarkProtocol(gates=gates, weights=weights)

    # Run settings
    runs = int(args.runs)
    warmup = int(args.warmup)
    if runs < 1:
        raise ValueError("--runs must be >= 1")
    if warmup < 0:
        raise ValueError("--warmup must be >= 0")

    # Warmup
    for wi in range(warmup):
        req = BelelHyperRequest(
            prompt=args.prompt,
            lyrics=args.lyrics,
            duration_sec=int(args.duration),
            filename=f"warmup_{wi}.wav",
            steps=int(args.steps),
            guidance=float(args.guidance),
            extra={"perf_claim": True, "warmup": True},
        )
        _reset_peak_vram(args.device)
        _cuda_sync(args.device)
        engine.run(req)
        _cuda_sync(args.device)

    # Measured runs
    times: List[float] = []
    vrams: List[float] = []
    scores: List[float] = []
    passes: List[bool] = []
    output_rows: List[Dict[str, Any]] = []

    for ri in range(runs):
        name = f"claim_s{int(args.steps)}_r{ri}.wav" if args.save_outputs else f"tmp_s{int(args.steps)}_r{ri}.wav"
        req = BelelHyperRequest(
            prompt=args.prompt,
            lyrics=args.lyrics,
            duration_sec=int(args.duration),
            filename=name,
            steps=int(args.steps),
            guidance=float(args.guidance),
            extra={"perf_claim": True, "warmup": False, "run_index": ri},
        )

        _reset_peak_vram(args.device)
        _cuda_sync(args.device)
        t0 = time.perf_counter()
        out = engine.run(req)
        _cuda_sync(args.device)
        t1 = time.perf_counter()

        dt = float(t1 - t0)
        times.append(dt)
        vrams.append(_peak_vram_gb(args.device))

        # Load mel from sidecar pt
        mel_obj = torch.load(out["mel_path"], map_location="cpu")
        mel = mel_obj["mel"] if isinstance(mel_obj, dict) and "mel" in mel_obj else mel_obj

        # NOTE: alignment_score is a placeholder until your Belel aligner module is plugged in.
        # Keep it explicit: we score acoustic proxies + gates now; alignment gets enforced when aligner lands.
        alignment_score = float(out["meta"].get("alignment_score", 0.0))

        score10, passed, breakdown = protocol.evaluate(mel, alignment_score=alignment_score)

        scores.append(float(score10))
        passes.append(bool(passed))

        row = {
            "run_index": ri,
            "time_sec": dt,
            "peak_vram_gb": vrams[-1],
            "score_10": float(score10),
            "passed": bool(passed),
            "breakdown": breakdown,
            "wav_path": out["wav_path"] if args.save_outputs else "",
            "mel_path": out["mel_path"] if args.save_outputs else "",
        }
        output_rows.append(row)

    # Aggregate
    measured = {
        "time_sec": _stats(times),
        "peak_vram_gb": _stats(vrams),
        "score_10": _stats(scores),
        "pass_rate": float(sum(passes) / max(1, len(passes))),
    }

    claim: Dict[str, Any] = {
        "utc": _utc_now(),
        "environment": env,
        "checkpoints": ckpts,
        "run": {
            "prompt": args.prompt,
            "lyrics_present": bool((args.lyrics or "").strip()),
            "duration_sec": int(args.duration),
            "steps": int(args.steps),
            "guidance": float(args.guidance),
            "dtype": str(args.dtype),
            "device": str(args.device),
            "seed": int(args.seed),
            "runs": runs,
            "warmup": warmup,
        },
        "protocol": {
            "gates": asdict(gates),
            "weights": asdict(weights),
        },
        "measured": measured,
        "outputs": output_rows,
    }

    # Write artifacts
    claim_json_path = str(Path(run_root) / "perf_claim.json")
    claim_md_path = str(Path(run_root) / "perf_claim.md")

    _write_json(claim_json_path, claim)
    _write_text(claim_md_path, _make_public_claim_block(claim))

    print("saved:", claim_json_path)
    print("saved:", claim_md_path)
    print(
        f"[CLAIM] avg_time={measured['time_sec']['avg']:.3f}s | "
        f"avg_peak_vram={measured['peak_vram_gb']['avg']:.3f}GB | "
        f"avg_score={measured['score_10']['avg']:.2f} | pass_rate={measured['pass_rate']:.2f}"
    )


if __name__ == "__main__":
    main()
