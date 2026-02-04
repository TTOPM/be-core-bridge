# BELEL-SING/belel-sing-gen/belel_benchmark_ultra.py
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

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
        if s < 1 or s > 6:
            raise ValueError("benchmark ceiling: steps must be in [1..6]")
    return steps


def _cuda_sync(device: str) -> None:
    if device.startswith("cuda") and torch.cuda.is_available():
        torch.cuda.synchronize()


def _reset_peak_vram(device: str) -> None:
    if device.startswith("cuda") and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()


def _peak_vram_gb(device: str) -> float:
    if device.startswith("cuda") and torch.cuda.is_available():
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
    ap.add_argument("--steps", default="6,4,2", help="e.g. '6,4,2' (ceiling: 6)")
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
    ap.add_argument("--save_outputs", action="store_true")
    ap.add_argument("--jsonl", action="store_true")

    args = ap.parse_args()

    steps_list = _parse_steps(args.steps)
    runs = int(args.runs)
    warmup = int(args.warmup)

    tag = args.tag or _now_utc_tag()
    run_root = os.path.join(args.out_dir, tag)
    _ensure_dir(run_root)

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
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prompt": args.prompt,
        "lyrics_present": bool(args.lyrics.strip()),
        "duration_sec": int(args.duration),
        "device": args.device,
        "dtype": args.dtype,
        "guidance": float(args.guidance),
        "seed": args.seed,
        "codec_ckpt": args.codec_ckpt,
        "denoiser_ckpt": args.denoiser_ckpt,
        "protocol": {
            "gates": vars(protocol.gates),
            "weights": vars(protocol.weights),
        },
        "results": {},
    }

    # --------------------------------------------------------
    # Benchmark loop
    # --------------------------------------------------------

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
                score=None,
                steps=int(steps),
                guidance=float(args.guidance),
                extra={"benchmark": True, "warmup": True},
            )
            _reset_peak_vram(args.device)
            _cuda_sync(args.device)
            engine.run(req)
            _cuda_sync(args.device)

        # Measured runs
        for ri in range(runs):
            name = f"bench_s{steps}_r{ri}.wav"
            req = BelelHyperRequest(
                prompt=args.prompt,
                lyrics=args.lyrics,
                duration_sec=int(args.duration),
                filename=name,
                score=None,
                steps=int(steps),
                guidance=float(args.guidance),
                extra={"benchmark": True, "run_index": ri},
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

            mel = torch.load(out["mel_path"], map_location="cpu")
            if isinstance(mel, dict) and "mel" in mel:
                mel = mel["mel"]

            score10, passed, breakdown = protocol.evaluate(
                mel,
                alignment_score=float(breakdown := 0.0),
            )

            scores.append(score10)
            passes.append(passed)

            outputs.append(
                {
                    "wav": out["wav_path"],
                    "mel": out["mel_path"],
                    "score_10": score10,
                    "passed": passed,
                    "breakdown": breakdown,
                }
            )

        summary["results"][str(steps)] = {
            "steps": int(steps),
            "runs": runs,
            "warmup": warmup,
            "time_sec": _human_stats(times),
            "peak_vram_gb": _human_stats(vrams),
            "score_10": _human_stats(scores),
            "pass_rate": float(sum(passes) / max(1, len(passes))),
            "outputs": outputs if args.save_outputs else outputs,
        }

        print(
            f"[steps={steps}] "
            f"avg_time={summary['results'][str(steps)]['time_sec']['avg']:.3f}s | "
            f"avg_score={summary['results'][str(steps)]['score_10']['avg']:.2f} | "
            f"pass_rate={summary['results'][str(steps)]['pass_rate']:.2f}"
        )

    # --------------------------------------------------------
    # Save report
    # --------------------------------------------------------

    report_path = os.path.join(run_root, "benchmark_summary.json")
    _write_json(report_path, summary)
    print("saved_summary:", report_path)

    if args.jsonl:
        _append_jsonl(os.path.join(args.out_dir, "benchmark_log.jsonl"), summary)
        print("appended_jsonl:", os.path.join(args.out_dir, "benchmark_log.jsonl"))


if __name__ == "__main__":
    main()
