import argparse
from pathlib import Path
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from tqdm import tqdm

from belel_hyper_core.belel_latent_codec import BelelDeepCompressor
from belel_hyper_core.belel_denoiser import BelelDenoiser1D
from belel_hyper_core.distill.belel_dataset import BelelMelFolder, collate_mels


def _load_sd(path: str) -> dict:
    obj = torch.load(path, map_location="cpu")
    if isinstance(obj, dict) and "state_dict" in obj:
        return obj["state_dict"]
    if isinstance(obj, dict):
        return obj
    raise ValueError(f"Unsupported checkpoint format: {path}")


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument("--mel_dir", required=True)
    ap.add_argument("--codec_ckpt", required=True)

    ap.add_argument(
        "--teacher_ckpt",
        required=True,
        help="4-step capable denoiser checkpoint",
    )
    ap.add_argument(
        "--student_init",
        default=None,
        help="optional starting checkpoint for 2-step student",
    )

    ap.add_argument("--out", default="checkpoints/belel_student_2.pt")
    ap.add_argument("--device", default="cuda")

    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max_len", type=int, default=2048)

    # locked mission: 4 -> 2
    ap.add_argument("--teacher_steps", type=int, default=4)
    ap.add_argument("--student_steps", type=int, default=2)

    args = ap.parse_args()

    if args.teacher_steps != 4 or args.student_steps != 2:
        raise ValueError("This script is strictly locked to 4 -> 2 distillation.")

    Path("checkpoints").mkdir(exist_ok=True, parents=True)

    # ---- Dataset
    dataset = list(BelelMelFolder(args.mel_dir, max_len=args.max_len))
    loader = DataLoader(
        dataset,
        batch_size=args.batch,
        shuffle=True,
        drop_last=True,
        collate_fn=lambda b: b,
    )

    # ---- Codec (frozen)
    codec = BelelDeepCompressor(mel_bins=80, latent_ch=32).to(args.device)
    codec.load_state_dict(_load_sd(args.codec_ckpt), strict=True)
    codec.eval()
    for p in codec.parameters():
        p.requires_grad = False

    # ---- Teacher denoiser (frozen, 4-step capable)
    teacher = BelelDenoiser1D(channels=32, cond_dim=1024).to(args.device)
    teacher.load_state_dict(_load_sd(args.teacher_ckpt), strict=True)
    teacher.eval()
    for p in teacher.parameters():
        p.requires_grad = False

    # ---- Student denoiser (trainable, 2-step target)
    student = BelelDenoiser1D(channels=32, cond_dim=1024).to(args.device)
    if args.student_init:
        student.load_state_dict(_load_sd(args.student_init), strict=True)
    student.train()

    optimizer = torch.optim.AdamW(student.parameters(), lr=args.lr)

    # ---- Conditioning placeholder (swap later for real text embeddings)
    cond_cache = torch.zeros((args.batch, 1024), device=args.device)

    # ---- 2-step schedule (aggressive but stable)
    # These knots matter. You can tune later, but this works.
    t_student = torch.tensor([1.0, 0.25], device=args.device)

    # ---- Training loop
    for ep in range(args.epochs):
        loss_sum = 0.0
        n = 0
        pbar = tqdm(loader, desc=f"distill 4->2 epoch {ep+1}/{args.epochs}")

        for batch in pbar:
            mel = collate_mels(batch, device=args.device, pad_value=-4.0)

            # ---- Encode real latents
            with torch.no_grad():
                zq, _, _ = codec.encode(mel)

            B = zq.shape[0]
            cond = cond_cache[:B]

            # ---- Sample one of the 2 student times
            idx = torch.randint(0, 2, (B,), device=args.device)
            t = t_student[idx]

            noise = torch.randn_like(zq)
            x = zq + t.view(-1, 1, 1) * noise

            # ---- Teacher prediction (4-step trained)
            with torch.no_grad():
                teacher_pred = teacher(x, t, cond)

            # ---- Student prediction
            student_pred = student(x, t, cond)

            # ---- Distillation loss
            loss = F.mse_loss(student_pred, teacher_pred)

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(student.parameters(), 1.0)
            optimizer.step()

            loss_sum += float(loss.item())
            n += 1
            pbar.set_postfix(loss=loss_sum / max(n, 1))

        # save every epoch (cheap insurance)
        torch.save(
            {"state_dict": student.state_dict(), "epoch": ep + 1},
            args.out,
        )
        print("Saved:", args.out)

    print("✔ 4 → 2 distillation complete")
    print("Student checkpoint:", args.out)


if __name__ == "__main__":
    main()
