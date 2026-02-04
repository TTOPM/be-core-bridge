import argparse
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Any, Optional

import torch

from belel_hyper_core.belel_engine import (
    BelelHyperEngine,
    BelelHyperConfig,
    BelelHyperRequest,
)


def _now_utc_tag() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.gmtime())


def _parse_steps(steps_str: str) -> List[int]:
    # supports: "6" or "6,4,2"
    parts = [p.strip() for p in (steps_str or "").split(",") if p.strip()]
    if not parts:
        raise ValueError("steps must be provided, e.g. '6' or '6,4,2'")
    steps = [int(p) for p in parts]
    for s in steps:
        if s < 1 or s > 6:
            raise ValueError("Belel benchmark ceiling: steps must be in [1..6]")
    return steps


def _ensure_dir(p: str) -> None:
    Path(p).mkdir(parents=True, exist_ok=True)


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


def _human_stats(times: List[float]) -> Dict[str, float]:
    if not times:
        return {"avg": 0.0, "p50": 0.0, "p90": 0.0, "min": 0.0, "max": 0.0}
    xs = sorted(times)
    n = len(xs)

    def q(p: float) -> float:
        if n == 1:
            return xs[0]
        i = int(round((n - 1) * p))
        i = max(0, min(n - 1, i))
        return xs[i]

    return {
        "avg": float(sum(xs) / n),
        "p50": float(q(0.50)),
        "p90": float(q(0.90)),
        "min": float(xs[0]),
        "max": float(xs[-1]),
    }


def main():
    ap = argparse.ArgumentParser()

    # generation content
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--lyrics", default="")
    ap.add_argument("--duration", type=int, default=60)

    # benchmark dimensions
    ap.add_argument("--steps", default="6", help="Single or list, e.g. '6' or '6,4,2' (hard ceiling: 6)")
    ap.add_argument("--runs", type=int, default=3, help="Measured runs per steps setting")
    ap.add_argument("--warmup", type=int, default=1, help="Warmup runs per steps setting (not counted)")

    # engine config
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dtype", default="float16")
    ap.add_argument("--guidance", type=float, default=6.5)
    ap.add_argument("--seed", type=int, default=None)

    # checkpoints
    ap.add_argument("--codec_ckpt", required=True)
    ap.add_argument("--denoiser_ckpt", required=True)

    # output
    ap.add_argument("--out_dir", default="benchmarks/belel_ultra")
    ap.add_argument("--tag", default=None, help="Optional run tag (folder label)")
    ap.add_argument("--save_outputs", action="store_true", help="Save wav+mel for each measured run")
    ap.add_argument("--jsonl", action="store_true", help="Append results to jsonl log in out_dir")

    args = ap.parse_args()

    steps_list = _parse_steps(args.steps)
    runs = int(args.runs)
    warmup = int(args.warmup)
    if runs < 1:
        raise ValueError("--runs must be >= 1")
    if warmup < 0:
        raise ValueError("--warmup must be >= 0")

    tag = args.tag or _now_utc_tag()
    run_root = os.path.join(args.out_dir, tag)
    _ensure_dir(run_root)

    # configure engine (loads your vocoder via infer.py)
    cfg = BelelHyperConfig(
        device=args.device,
        dtype=args.dtype,
        steps=6,  # engine ceiling; actual steps passed per-request
        guidance=float(args.guidance),
        seed=args.seed,
        out_dir=os.path.join(run_root, "outputs"),
        codec_ckpt=args.codec_ckpt,
        denoiser_ckpt=args.denoiser_ckpt,
    )

    engine = BelelHyperEngine(cfg)
    engine.load_checkpoints()
    engine.to_device()

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
        "results": {},
    }

    # bench loop
    for steps in steps_list:
        times: List[float] = []
        peak_vrams: List[float] = []
        out_paths: List[Dict[str, str]] = []

        # warmup
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
            _ = engine.run(req)
            _cuda_sync(args.device)

        # measured runs
        for ri in range(runs):
            name = f"bench_s{steps}_r{ri}.wav" if args.save_outputs else f"tmp_s{steps}_r{ri}.wav"
            req = BelelHyperRequest(
                prompt=args.prompt,
                lyrics=args.lyrics,
                duration_sec=int(args.duration),
                filename=name,
                score=None,
                steps=int(steps),
                guidance=float(args.guidance),
                extra={"benchmark": True, "warmup": False, "run_index": ri},
            )

            _reset_peak_vram(args.device)
            _cuda_sync(args.device)
            t0 = time.perf_counter()
            out = engine.run(req)
            _cuda_sync(args.device)
            t1 = time.perf_counter()

            dt = float(t1 - t0)
            times.append(dt)
            peak_vrams.append(_peak_vram_gb(args.device))

            if args.save_outputs:
                out_paths.append({"wav": out["wav_path"], "mel": out["mel_path"]})
            else:
                # still record paths for debugging; files exist unless you delete them
                out_paths.append({"wav": out["wav_path"], "mel": out["mel_path"]})

        stats = _human_stats(times)
        vram_stats = _human_stats(peak_vrams)

        summary["results"][str(steps)] = {
            "steps": int(steps),
            "runs": runs,
            "warmup": warmup,
            "time_sec": stats,
            "peak_vram_gb": vram_stats,
            "outputs": out_paths if args.save_outputs else out_paths,
        }

        # print compact line per steps
        print(
            f"[steps={steps}] avg={stats['avg']:.3f}s p50={stats['p50']:.3f}s p90={stats['p90']:.3f}s "
            f"peakVRAM(avg)={vram_stats['avg']:.3f}GB"
        )

    # save report
    report_path = os.path.join(run_root, "benchmark_summary.json")
    _write_json(report_path, summary)
    print("saved_summary:", report_path)

    if args.jsonl:
        _append_jsonl(os.path.join(args.out_dir, "benchmark_log.jsonl"), summary)
        print("appended_jsonl:", os.path.join(args.out_dir, "benchmark_log.jsonl"))


if __name__ == "__main__":
    main()
