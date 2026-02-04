import argparse
import torch

from belel_hyper_core.belel_engine import BelelHyperEngine, BelelHyperConfig, BelelHyperRequest
from belel_hyper_core.distill.belel_evolution_tracker import BelelEvolutionTracker


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--lyrics", default="")
    ap.add_argument("--duration", type=int, default=240)

    ap.add_argument("--steps", type=int, default=6)
    ap.add_argument("--guidance", type=float, default=6.5)
    ap.add_argument("--dtype", default="float16")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--device", default="cuda")

    ap.add_argument("--out_dir", default="outputs/belel_ultra")
    ap.add_argument("--name", default=None)
    ap.add_argument("--score", type=float, default=None)
    args = ap.parse_args()

    cfg = BelelHyperConfig(
        device=args.device,
        dtype=args.dtype,
        steps=args.steps,
        guidance=args.guidance,
        seed=args.seed,
        out_dir=args.out_dir,
        mel_bins=80,
        sample_rate=22050,
        hop_length=256,
        win_length=1024,
    )

    engine = BelelHyperEngine(cfg).to_device()
    req = BelelHyperRequest(
        prompt=args.prompt,
        lyrics=args.lyrics,
        duration_sec=args.duration,
        filename=args.name,
        score=args.score,
    )

    out = engine.run(req)
    print("saved:", out["path"])
    print("mel:", tuple(out["mel"].shape))
    print("wav:", tuple(out["wav"].shape))

    if args.device.startswith("cuda") and torch.cuda.is_available():
        print("peak_vram_gb:", round(torch.cuda.max_memory_allocated() / (1024**3), 3))

    if args.score is not None:
        tracker = BelelEvolutionTracker()
        tracker.log(args.prompt, args.lyrics, out["path"], args.score)
        print("evolution_logged")

if __name__ == "__main__":
    main()
