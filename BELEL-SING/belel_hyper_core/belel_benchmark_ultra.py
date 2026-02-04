import argparse
import time
import torch
import statistics

from belel_hyper_core.belel_engine import (
    BelelHyperEngine,
    BelelHyperConfig,
    BelelHyperRequest,
)


def benchmark_run(
    engine: BelelHyperEngine,
    prompt: str,
    lyrics: str,
    duration: int,
    steps: int,
    guidance: float,
):
    torch.cuda.reset_peak_memory_stats()

    start = time.perf_counter()
    out = engine.run(
        BelelHyperRequest(
            prompt=prompt,
            lyrics=lyrics,
            duration_sec=duration,
            steps=steps,
            guidance=guidance,
        )
    )
    end = time.perf_counter()

    elapsed = end - start

    if torch.cuda.is_available():
        peak_vram = torch.cuda.max_memory_allocated() / (1024 ** 3)
    else:
        peak_vram = 0.0

    return {
        "seconds": elapsed,
        "peak_vram_gb": peak_vram,
        "wav_path": out["wav_path"],
        "mel_path": out["mel_path"],
    }


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--prompt", required=True)
    ap.add_argument("--lyrics", default="")
    ap.add_argument("--duration", type=int, default=60)

    ap.add_argument("--steps", type=int, default=6, help="Benchmark ceiling: must be <= 6")
    ap.add_argument("--guidance", type=float, default=6.5)

    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--warmup", type=int, default=1)

    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dtype", default="float16")

    ap.add_argument("--codec_ckpt", required=True)
    ap.add_argument("--denoiser_ckpt", required=True)

    ap.add_argument("--out_dir", default="outputs/belel_ultra")

    args = ap.parse_args()

    if args.steps > 6:
        raise ValueError("Benchmark ceiling violated: steps must be <= 6")

    cfg = BelelHyperConfig(
        device=args.device,
        dtype=args.dtype,
        steps=args.steps,
        guidance=args.guidance,
        out_dir=args.out_dir,
        codec_ckpt=args.codec_ckpt,
        denoiser_ckpt=args.denoiser_ckpt,
    )

    engine = BelelHyperEngine(cfg)
    engine.load_checkpoints()
    engine.to_device()

    # Warmup runs (not counted)
    for _ in range(args.warmup):
        engine.run(
            BelelHyperRequest(
                prompt=args.prompt,
                lyrics=args.lyrics,
                duration_sec=args.duration,
                steps=args.steps,
                guidance=args.guidance,
            )
        )

    results = []
    for i in range(args.runs):
        res = benchmark_run(
            engine,
            prompt=args.prompt,
            lyrics=args.lyrics,
            duration=args.duration,
            steps=args.steps,
            guidance=args.guidance,
        )
        results.append(res)
        print(
            f"Run {i+1}: "
            f"{res['seconds']:.3f}s, "
            f"peak VRAM {res['peak_vram_gb']:.3f} GB"
        )

    times = [r["seconds"] for r in results]
    vrams = [r["peak_vram_gb"] for r in results]

    print("\n=== BELEL ULTRA BENCHMARK SUMMARY ===")
    print(f"Steps: {args.steps}")
    print(f"Runs: {args.runs}")
    print(f"Mean time: {statistics.mean(times):.3f}s")
    print(f"Median time: {statistics.median(times):.3f}s")
    print(f"Min time: {min(times):.3f}s")
    print(f"Max time: {max(times):.3f}s")

    if torch.cuda.is_available():
        print(f"Peak VRAM (max): {max(vrams):.3f} GB")

    print("====================================")


if __name__ == "__main__":
    main()
