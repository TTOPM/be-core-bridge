import argparse
from pathlib import Path
import torch
import torch.nn.functional as F
from tqdm import tqdm

from belel_hyper_core.belel_latent_codec import BelelDeepCompressor
from belel_hyper_core.belel_denoiser import BelelDenoiser1D
from belel_hyper_core.distill.belel_evolution_tracker import BelelEvolutionTracker


def _load_sd(path: str) -> dict:
    obj = torch.load(path, map_location="cpu")
    if isinstance(obj, dict) and "state_dict" in obj:
        return obj["state_dict"]
    if isinstance(obj, dict):
        return obj
    raise ValueError(f"Unsupported checkpoint format: {path}")


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--codec_ckpt", required=True)
    ap.add_argument("--student_ckpt", required=True)
    ap.add_argument("--out", default="checkpoints/belel_student_evolved.pt")

    ap.add_argument("--device", default="cuda")
    ap.add_argument("--min_score", type=float, default=8.0)
    ap.add_argument("--limit", type=int, default=128)

    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--batch", type=int, default=8)

    args = ap.parse_args()
    Path("checkpoints").mkdir(parents=True, exist_ok=True)

    # ---- Load scored evolution entries
    tracker = BelelEvolutionTracker()
    items = tracker.select(min_score=args.min_score, limit=args.limit)
    if not items:
        raise SystemExit("No scored generations found.")

    # ---- Load codec (frozen)
    codec = BelelDeepCompressor(mel_bins=80, latent_ch=32).to(args.device)
    codec.load_state_dict(_load_sd(args.codec_ckpt), strict=True)
    codec.eval()
    for p in codec.parameters():
        p.requires_grad = False

    # ---- Load student denoiser (trainable)
    student = BelelDenoiser1D(channels=32, cond_dim=1024).to(args.device)
    student.load_state_dict(_load_sd(args.student_ckpt), strict=True)
    student.train()

    opt = torch.optim.AdamW(student.parameters(), lr=args.lr)

    # ---- Collect real latents via codec.encode
    latents = []
    for it in items:
        mel_obj = torch.load(it.mel_path, map_location="cpu")
        mel = mel_obj["mel"] if isinstance(mel_obj, dict) else mel_obj
        if mel.ndim == 3:
            mel = mel[0]
        mel = mel.unsqueeze(0).to(args.device)

        with torch.no_grad():
            zq, _, _ = codec.encode(mel)
        latents.append(zq)

    # ---- Student step schedule (4-step default)
    t_knots = torch.tensor([1.0, 0.66, 0.33, 0.10], device=args.device)

    # ---- Training loop
    for ep in range(args.epochs):
        pbar = tqdm(latents, desc=f"evolve epoch {ep+1}/{args.epochs}")
        loss_sum = 0.0
        n = 0

        for i in range(0, len(latents), args.batch):
            batch = latents[i : i + args.batch]
            x0 = torch.cat(batch, dim=0)
            B = x0.shape[0]

            cond = torch.zeros((B, 1024), device=args.device)

            idx = torch.randint(0, len(t_knots), (B,), device=args.device)
            t = t_knots[idx]

            noise = torch.randn_like(x0)
            x = x0 + t.view(-1, 1, 1) * noise

            pred = student(x, t, cond)
            loss = F.mse_loss(pred, noise)

            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(student.parameters(), 1.0)
            opt.step()

            loss_sum += float(loss.item())
            n += 1
            pbar.set_postfix(loss=loss_sum / max(n, 1))

    torch.save({"state_dict": student.state_dict()}, args.out)
    print("Saved evolved student:", args.out)


if __name__ == "__main__":
    main()
