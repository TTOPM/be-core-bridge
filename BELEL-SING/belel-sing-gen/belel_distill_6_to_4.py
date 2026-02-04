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

    ap.add_argument("--teacher_ckpt", required=True, help="6-step capable denoiser")
    ap.add_argument("--student_init", default=None, help="optional starting point for student")

    ap.add_argument("--out", default="checkpoints/belel_student_4.pt")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max_len", type=int, default=2048)

    # 6->4 is the mission here
    ap.add_argument("--teacher_steps", type=int, default=6)
    ap.add_argument("--student_steps", type=int, default=4)

    args = ap.parse_args()
    if args.teacher_steps != 6 or args.student_steps != 4:
        raise ValueError("This script is locked to 6->4 for clarity. Clone it for 4->2 later.")

    ds = list(BelelMelFolder(args.mel_dir, max_len=args.max_len))
    dl = DataLoader(ds, batch_size=args.batch, shuffle=True, drop_last=True, collate_fn=lambda b: b)

    Path("checkpoints").mkdir(exist_ok=True, parents=True)

    # codec (frozen)
    codec = BelelDeepCompressor(mel_bins=80, latent_ch=32).to(args.device)
    codec.load_state_dict(_load_sd(args.codec_ckpt), strict=True)
    codec.eval()
    for p in codec.parameters():
        p.requires_grad = False

    # teacher (frozen)
    teacher = BelelDenoiser1D(channels=32, cond_dim=1024).to(args.device)
    teacher.load_state_dict(_load_sd(args.teacher_ckpt), strict=True)
    teacher.eval()
    for p in teacher.parameters():
        p.requires_grad = False

    # student (trainable)
    student = BelelDenoiser1D(channels=32, cond_dim=1024).to(args.device)
    if args.student_init:
        student.load_state_dict(_load_sd(args.student_init), strict=True)

    opt = torch.optim.AdamW(student.parameters(), lr=args.lr)

    # conditioning placeholder: zeros (swap to your paired text embedding dataset when ready)
    cond_cache = torch.zeros((args.batch, 1024), device=args.device)

    # Define a coarse 4-step t schedule. We train student at these t values.
    # In practice you can tune these knots.
    t_student = torch.tensor([1.0, 0.66, 0.33, 0.10], device=args.device)

    for ep in range(args.epochs):
        student.train()
        pbar = tqdm(dl, desc=f"distill 6->4 epoch {ep+1}/{args.epochs}")
        loss_sum = 0.0
        n = 0

        for batch in pbar:
            mel = collate_mels(batch, device=args.device, pad_value=-4.0)

            with torch.no_grad():
                zq, _, _ = codec.encode(mel)

            B = zq.shape[0]
            cond = cond_cache[:B]

            # sample one of the 4 step times
            idx = torch.randint(0, 4, (B,), device=args.device)
            t = t_student[idx]  # [B]
            noise = torch.randn_like(zq)
            x = zq + t.view(-1, 1, 1) * noise

            with torch.no_grad():
                teacher_pred = teacher(x, t, cond)

            student_pred = student(x, t, cond)

            # distill target: match teacher prediction
            loss = F.mse_loss(student_pred, teacher_pred)

            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(student.parameters(), 1.0)
            opt.step()

            loss_sum += float(loss.item())
            n += 1
            pbar.set_postfix(loss=loss_sum / max(n, 1))

        torch.save({"state_dict": student.state_dict(), "epoch": ep + 1}, args.out)
        print("saved:", args.out)


if __name__ == "__main__":
    main()
