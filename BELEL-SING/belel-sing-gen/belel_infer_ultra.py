import argparse
import torch

from belel_hyper_core.belel_engine import BelelHyperEngine, BelelHyperConfig, BelelHyperRequest

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
    args = ap.parse_args()

    cfg = BelelHyperConfig(
        device=args.device,
        dtype=args.dtype,
        steps=args.steps,
        guidance=args.guidance,
        seed=args.seed,
    )
    engine = BelelHyperEngine(cfg).to_device()
    out = engine.run(BelelHyperRequest(prompt=args.prompt, lyrics=args.lyrics, duration_sec=args.duration))

    mel = out["mel"]
    print("mel shape:", tuple(mel.shape))
    if args.device.startswith("cuda") and torch.cuda.is_available():
        print("peak vram (GB):", round(torch.cuda.max_memory_allocated() / (1024**3), 3))

if __name__ == "__main__":
    main()
