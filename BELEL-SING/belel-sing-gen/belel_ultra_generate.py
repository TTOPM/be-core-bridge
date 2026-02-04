import argparse
import torch

from belel_hyper_core.belel_engine import BelelHyperEngine, BelelHyperConfig, BelelHyperRequest


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--prompt", required=True)
    ap.add_argument("--lyrics", default="")
    ap.add_argument("--duration", type=int, default=240)

    ap.add_argument("--steps", type=int, default=6, help="Benchmark ceiling: 6 or less.")
    ap.add_argument("--guidance", type=float, default=6.5)
    ap.add_argument("--dtype", default="float16")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--device", default="cuda")

    ap.add_argument("--out_dir", default="outputs/belel_ultra")
    ap.add_argument("--name", default=None)

    ap.add_argument("--codec_ckpt", default=None)
    ap.add_argument("--denoiser_ckpt", default=None)

    ap.add_argument("--score", type=float, default=None)
    args = ap.parse_args()

    cfg = BelelHyperConfig(
        device=args.device,
        dtype=args.dtype,
        steps=args.steps,
        guidance=args.guidance,
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
        duration_sec=args.duration,
        filename=args.name,
        score=args.score,
        steps=args.steps,
        guidance=args.guidance,
    )

    out = engine.run(req)
    print("wav:", out["wav_path"])
    print("mel:", out["mel_path"])
    print("mel_shape:", tuple(out["mel"].shape))
    print("wav_shape:", tuple(out["wav"].shape))

    if args.device.startswith("cuda") and torch.cuda.is_available():
        print("peak_vram_gb:", round(torch.cuda.max_memory_allocated() / (1024**3), 3))


if __name__ == "__main__":
    main()
