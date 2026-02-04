# BELEL-SING/belel-sing-gen/belel_benchmark_ultra.py
from __future__ import annotations

import argparse
import json
import os
import platform
import time
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

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

def _utc_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _now_utc_tag() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.gmtime())


def _ensure_dir(p: str) -> None:
    Path(p).mkdir(parents=True, exist_ok=True)


def _parse_steps(steps_str: str) -> List[int]:
    parts = [p.strip() for p in (steps_str or "").split(",") if p.strip()]
    if not parts:
        raise ValueError("steps must be provided, e.g. '6' or '6,4,2'")
    steps = [int(p) for p in parts]
    for s in steps:
        if s not in (2, 4, 6):
            raise ValueError("Belel Ultra benchmark: steps must be one of: 2,4,6")
    return steps


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


def _write_json(path: str, obj: Dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _append_jsonl(path: str, obj: Dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _human_stats(xs: List[float]) -> Dict[str, float]:
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


def _load_mel_from_pt(mel_pt_path: str) -> torch.Tensor:
    obj = torch.load(mel_pt_path, map_location="cpu")
    if isinstance(obj, dict) and "mel" in obj:
        mel = obj["mel"]
    else:
        mel = obj
    if not isinstance(mel, torch.Tensor):
        raise TypeError(f"mel sidecar did not contain a Tensor: {mel_pt_path}")
    if mel.ndim == 3 and mel.shape[0] == 1:
        mel = mel[0]
    return mel.float().cpu()


def _device_info(device: str) -> Dict[str, Any]:
    info: Dict[str, Any] = {
        "device": str(device),
        "torch_version": torch.__version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    if str(device).startswith("cuda") and torch.cuda.is_available():
        try:
            info["cuda_available"] = True
            info["cuda_version"] = torch.version.cuda
            info["cudnn_version"] = torch.backends.cudnn.version()
            info["gpu_name"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            info["gpu_total_vram_gb"] = float(props.total_memory / (1024 ** 3))
        except Exception:
            pass
    else:
        info["cuda_available"] = False
    return info


def _public_claim_lines(
    *,
    model_tag: str,
    steps: int,
    duration_sec: int,
    time_stats: Dict[str, float],
    vram_stats: Dict[str, float],
    score_stats: Dict[str, float],
    pass_rate: float,
) -> Dict[str, str]:
    """
    Produces standardized, defensible claim lines based solely on measured stats.
    """
    avg_time = float(time_stats.get("avg", 0.0))
    p50_time = float(time_stats.get("p50", 0.0))
    p90_time = float(time_stats.get("p90", 0.0))

    rtf_avg = (float(duration_sec) / avg_time) if avg_time > 1e-9 else 0.0
    rtf_p50 = (float(duration_sec) / p50_time) if p50_time > 1e-9 else 0.0
    rtf_p90 = (float(duration_sec) / p90_time) if p90_time > 1e-9 else 0.0

    avg_vram = float(vram_stats.get("avg", 0.0))
    avg_score = float(score_stats.get("avg", 0.0))

    headline = (
        f"{model_tag} Ultra ({steps}-step): {duration_sec}s generated in "
        f"{avg_time:.2f}s avg (p50 {p50_time:.2f}s, p90 {p90_time:.2f}s) | "
        f"RTF avg {rtf_avg:.2f}× (p50 {rtf_p50:.2f}×, p90 {rtf_p90:.2f}×) | "
        f"peak VRAM avg {avg_vram:.2f} GB | quality score avg {avg_score:.2f}/10 | "
        f"pass rate {pass_rate:.2f}"
    )

    strict = (
        f"Measured claim: {duration_sec}s audio → avg {avg_time:.2f}s, p90 {p90_time:.2f}s at {steps} steps; "
        f"RTF avg {rtf_avg:.2f}×; peak VRAM avg {avg_vram:.2f} GB; score avg {avg_score:.2f}/10; pass {pass_rate:.2f}."
    )

    return {"headline": headline, "strict": strict}


# ============================================================
# Main benchmark runner
# ============================================================

def main():
    ap = argparse.ArgumentParser()

    # Content
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--lyrics", default="")
    ap.add_argument("--duration", type=int, default=60)

    # Benchmark dimensions
    ap.add_argument("--steps", default="6,4,2", help="e.g. '6,4,2' (allowed: 6,4,2)")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--warmup", type=int, default=1)

    # Engine config
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dtype", default="float16")
    ap.add_argument("--guidance", type=float, default=6.0)
    ap.add_argument("--seed", type=int, default=None)

    # Checkpoints
    ap.add_argument("--codec_ckpt", required=True)
    ap.add_argument("--denoiser_ckpt", required=True)

    # Output
    ap.add_argument("--out_dir", default="benchmarks/belel_ultra")
    ap.add_argument("--tag", default=None)

    # Storage controls
    ap.add_argument("--save_outputs", action="store_true", help="Keep wav/mel artifacts for measured runs")
    ap.add_argument("--keep_warmups", action="store_true", help="Keep warmup artifacts too (usually no)")
    ap.add_argument("--jsonl", action="store_true", help="Append summary to out_dir/benchmark_log.jsonl")

    # Protocol controls
    ap.add_argument("--require_pass_all", action="store_true", help="Fail the entire run if any measured sample fails")
    ap.add_argument("--alignment_score", type=float, default=0.0, help="Optional external aligner score in [0..1]")

    # Metadata
    ap.add_argument("--model_tag", default="BELEL-SING", help="Printed into claim lines and reports")
    ap.add_argument("--run_note", default="", help="Freeform note stored in report")

    args = ap.parse_args()

    steps_list = _parse_steps(args.steps)
    runs = int(args.runs)
    warmup = int(args.warmup)
    if runs < 1:
        raise ValueError("--runs must be >= 1")
    if warmup < 0:
        raise ValueError("--warmup must be >= 0")
    if int(args.duration) < 1:
        raise ValueError("--duration must be >= 1")

    tag = args.tag or _now_utc_tag()
    run_root = os.path.join(args.out_dir, tag)
    _ensure_dir(run_root)
    _ensure_dir(os.path.join(run_root, "outputs"))

    # --------------------------------------------------------
    # Engine
    # --------------------------------------------------------

    cfg = BelelHyperConfig(
        device=args.device,
        dtype=args.dtype,
        steps=6,  # engine ceiling
        guidance=float(args.guidance),
        seed=args.seed,
        out_dir=os.path.join(run_root, "outputs"),
        codec_ckpt=args.codec_ckpt,
        denoiser_ckpt=args.denoiser_ckpt,
    )

    engine = BelelHyperEngine(cfg)
    engine.load_checkpoints()
    engine.to_device()

    # --------------------------------------------------------
    # Benchmark protocol (authoritative judge)
    # --------------------------------------------------------

    protocol = BelelBenchmarkProtocol(
        gates=BelelBenchmarkGates(),
        weights=BelelBenchmarkWeights(),
    )

    summary: Dict[str, Any] = {
        "tag": tag,
        "utc": _utc_iso(),
        "model_tag": str(args.model_tag),
        "run_note": str(args.run_note),
        "content": {
            "prompt": args.prompt,
            "lyrics_present": bool(args.lyrics.strip()),
            "duration_sec": int(args.duration),
        },
        "engine": {
            "device": args.device,
            "dtype": args.dtype,
            "guidance": float(args.guidance),
            "seed": args.seed,
            "codec_ckpt": args.codec_ckpt,
            "denoiser_ckpt": args.denooiser_ckpt if hasattr(args, "denooiser_ckpt") else args.denoiser_ckpt,
        },
        "device_info": _device_info(args.device),
        "protocol": {
            "gates": asdict(protocol.gates),
            "weights": asdict(protocol.weights),
        },
        "results": {},
        "claims": {},
        "run_passed": True,
    }

    # --------------------------------------------------------
    # Benchmark loop
    # --------------------------------------------------------

    overall_fail = False

    for steps in steps_list:
        times: List[float] = []
        vrams: List[float] = []
        scores: List[float] = []
        passes: List[bool] = []
        outputs: List[Dict[str, Any]] = []

        # Warmup
        for wi in range(warmup):
            req = BelelHyperRequest(
                prompt=args.prompt,
                lyrics=args.lyrics,
                duration_sec=int(args.duration),
                filename=f"warmup_s{steps}_{wi}.wav",
                steps=int(steps),
                guidance=float(args.guidance),
                extra={"benchmark": True, "warmup": True, "step": int(steps), "run_index": wi},
            )
            _reset_peak_vram(args.device)
            _cuda_sync(args.device)
            out_w = engine.run(req)
            _cuda_sync(args.device)

            if not args.keep_warmups:
                # Optional cleanup of warmup artifacts
                try:
                    Path(out_w["wav_path"]).unlink(missing_ok=True)  # py3.8+ uses missing_ok in 3.8? (3.8 has it)
                except Exception:
                    pass
                try:
                    Path(out_w["mel_path"]).unlink(missing_ok=True)
                except Exception:
                    pass
                try:
                    Path(out_w["wav_sidecar"]).unlink(missing_ok=True)
                except Exception:
                    pass

        # Measured runs
        for ri in range(runs):
            name = f"bench_s{steps}_r{ri}.wav"
            req = BelelHyperRequest(
                prompt=args.prompt,
                lyrics=args.lyrics,
                duration_sec=int(args.duration),
                filename=name,
                steps=int(steps),
                guidance=float(args.guidance),
                extra={"benchmark": True, "warmup": False, "step": int(steps), "run_index": ri},
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

            mel = _load_mel_from_pt(out["mel_path"])

            # alignment_score: external for now (0..1); later your Belel aligner will feed this per-sample
            alignment = float(max(0.0, min(1.0, float(args.alignment_score))))

            score10, passed, breakdown = protocol.evaluate(
                mel,
                alignment_score=alignment,
                duration_sec=int(args.duration),
                wall_time_sec=dt,
                peak_vram_gb=float(vrams[-1]),
            )

            scores.append(float(score10))
            passes.append(bool(passed))

            outputs.append(
                {
                    "wav": out["wav_path"],
                    "mel": out["mel_path"],
                    "wav_sidecar": out["wav_sidecar"],
                    "elapsed_sec": dt,
                    "peak_vram_gb": float(vrams[-1]),
                    "rtf": float(int(args.duration) / dt) if dt > 1e-9 else 0.0,
                    "alignment_score": alignment,
                    "score_10": float(score10),
                    "passed": bool(passed),
                    "breakdown": breakdown,
                }
            )

            # Optional cleanup if user doesn't want outputs
            if not args.save_outputs:
                try:
                    Path(out["wav_path"]).unlink(missing_ok=True)
                except Exception:
                    pass
                try:
                    Path(out["mel_path"]).unlink(missing_ok=True)
                except Exception:
                    pass
                try:
                    Path(out["wav_sidecar"]).unlink(missing_ok=True)
                except Exception:
                    pass

        time_stats = _human_stats(times)
        vram_stats = _human_stats(vrams)
        score_stats = _human_stats(scores)
        pass_rate = float(sum(1 for p in passes if p) / max(1, len(passes)))

        step_block = {
            "steps": int(steps),
            "runs": runs,
            "warmup": warmup,
            "time_sec": time_stats,
            "peak_vram_gb": vram_stats,
            "rtf": {
                "avg": float((int(args.duration) / time_stats["avg"]) if time_stats["avg"] > 1e-9 else 0.0),
                "p50": float((int(args.duration) / time_stats["p50"]) if time_stats["p50"] > 1e-9 else 0.0),
                "p90": float((int(args.duration) / time_stats["p90"]) if time_stats["p90"] > 1e-9 else 0.0),
                "min": float((int(args.duration) / time_stats["max"]) if time_stats["max"] > 1e-9 else 0.0),
                "max": float((int(args.duration) / time_stats["min"]) if time_stats["min"] > 1e-9 else 0.0),
            },
            "score_10": score_stats,
            "pass_rate": pass_rate,
            "outputs": outputs,
        }

        summary["results"][str(steps)] = step_block

        # Public claim lines per steps mode
        summary["claims"][str(steps)] = _public_claim_lines(
            model_tag=str(args.model_tag),
            steps=int(steps),
            duration_sec=int(args.duration),
            time_stats=time_stats,
            vram_stats=vram_stats,
            score_stats=score_stats,
            pass_rate=pass_rate,
        )

        # Decide if run fails
        if args.require_pass_all and pass_rate < 1.0:
            overall_fail = True

        print(
            f"[steps={steps}] "
            f"avg_time={time_stats['avg']:.3f}s | "
            f"avg_rtf={summary['results'][str(steps)]['rtf']['avg']:.2f}x | "
            f"avg_score={score_stats['avg']:.2f} | "
            f"pass_rate={pass_rate:.2f} | "
            f"avg_peakVRAM={vram_stats['avg']:.3f}GB"
        )

    summary["run_passed"] = (not overall_fail)

    # --------------------------------------------------------
    # Save report
    # --------------------------------------------------------

    report_path = os.path.join(run_root, "benchmark_summary.json")
    _write_json(report_path, summary)
    print("saved_summary:", report_path)

    claims_path = os.path.join(run_root, "public_claims.json")
    _write_json(claims_path, {"tag": tag, "utc": _utc_iso(), "claims": summary["claims"], "run_passed": summary["run_passed"]})
    print("saved_claims:", claims_path)

    if args.jsonl:
        _append_jsonl(os.path.join(args.out_dir, "benchmark_log.jsonl"), summary)
        print("appended_jsonl:", os.path.join(args.out_dir, "benchmark_log.jsonl"))

    # Non-zero exit on fail (CI gate)
    if overall_fail:
        raise SystemExit("BENCHMARK FAILED: require_pass_all enabled and one or more samples failed protocol gates.")


if __name__ == "__main__":
    main()