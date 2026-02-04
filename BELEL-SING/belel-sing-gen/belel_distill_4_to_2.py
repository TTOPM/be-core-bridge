import argparse
from pathlib import Path
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader
from tqdm import tqdm

from belel_hyper_core.belel_latent_codec import BelelDeepCompressor
from belel_hyper_core.belel_denoiser import BelelDenoiser1D
from belel_hyper_core.distill.belel_dataset import BelelMelFolder, collate_mels
from belel_hyper_core.distill.belel_cfg_collapse import (
    belel_cfg_mix,
    belel_guidance_schedule,
    belel_guidance_dropout,
)


def _load_sd(path: str) -> dict:
    obj = torch.load(path, map_location="cpu")
    if isinstance(obj, dict) and "state_dict" in obj:
        return obj["state_dict"]
    if isinstance(obj, dict):
        return obj
    raise ValueError(f"Unsupported checkpoint format: {path}")


def _set_requires_grad(m: torch.nn.Module, flag: bool) -> None:
    for p in m.parameters():
        p.requires_grad = flag


def main():
    ap = argparse.ArgumentParser()

    # data + checkpoints
    ap.add_argument("--mel_dir", required=True)
    ap.add_argument("--codec_ckpt", required=True)
    ap.add_argument("--teacher_ckpt", required=True, help="4-step capable denoiser checkpoint")
    ap.add_argument("--student_init", default=None, help="Optional init checkpoint for 2-step student")
    ap.add_argument("--out", default="checkpoints/belel_student_2.pt")

    # runtime
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max_len", type=int, default=2048)
    ap.add_argument("--grad_clip", type=float, default=1.0)

    # locked mission
    ap.add_argument("--teacher_steps", type=int, default=4)
    ap.add_argument("--student_steps", type=int, default=2)

    # CFG-collapse (teacher-guided)
    ap.add_argument("--cfg_collapse", action="store_true", help="Enable teacher-guided CFG collapse")
    ap.add_argument("--cfg_weight", type=float, default=1.0, help="Weight for collapse loss term")
    ap.add_argument("--guidance_min", type=float, default=1.0)
    ap.add_argument("--guidance_max", type=float, default=7.5)
    ap.add_argument("--guidance_mode", default="snr", choices=["linear", "cosine", "snr"])
    ap.add_argument("--guidance_power", type=float, default=2.0, help="Only used for snr mode")
    ap.add_argument("--guidance_dropout_p", type=float, default=0.10, help="Drop guidance toward min")
    ap.add_argument("--mix_clamp", type=float, default=10.0, help="Clamp guided target magnitude")
    ap.add_argument("--dynamic_cap", action="store_true", help="Enable dynamic guidance capping")
    ap.add_argument("--cap_k", type=float, default=3.0, help="Dynamic cap aggressiveness")

    # conditioning (still operational even with zeros)
    ap.add_argument("--cond_dim", type=int, default=1024, help="Conditioning dimension expected by denoiser")
    ap.add_argument("--use_zero_cond", action="store_true", help="Use zero conditioning vectors (default).")

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
    _set_requires_grad(codec, False)

    # ---- Teacher (frozen)
    teacher = BelelDenoiser1D(channels=32, cond_dim=args.cond_dim).to(args.device)
    teacher.load_state_dict(_load_sd(args.teacher_ckpt), strict=True)
    teacher.eval()
    _set_requires_grad(teacher, False)

    # ---- Student (trainable)
    student = BelelDenoiser1D(channels=32, cond_dim=args.cond_dim).to(args.device)
    if args.student_init:
        student.load_state_dict(_load_sd(args.student_init), strict=True)
    student.train()
    _set_requires_grad(student, True)

    optimizer = torch.optim.AdamW(student.parameters(), lr=args.lr)

    # ---- 2-step schedule knots (stable aggressive defaults)
    # You can later try [1.0, 0.18] once stable.
    t_student = torch.tensor([1.0, 0.25], device=args.device)

    # ---- conditioning buffers (operational baseline)
    # If you haven't wired real embeddings yet, this still runs and trains the denoiser's core skill.
    # For CFG collapse to truly matter, cond must differ from uncond; zeros keep plumbing correct.
    cond_cache = torch.zeros((args.batch, args.cond_dim), device=args.device)
    uncond_cache = torch.zeros((args.batch, args.cond_dim), device=args.device)

    for ep in range(args.epochs):
        student.train()

        # teacher guidance schedule (epoch-wise)
        g_epoch = belel_guidance_schedule(
            epoch=ep,
            max_epoch=args.epochs,
            g_min=args.guidance_min,
            g_max=args.guidance_max,
            mode=args.guidance_mode,
            power=args.guidance_power,
        )

        loss_sum = 0.0
        n = 0

        pbar = tqdm(loader, desc=f"distill 4->2 ep {ep+1}/{args.epochs} (g={g_epoch:.2f})")

        for batch in pbar:
            mel = collate_mels(batch, device=args.device, pad_value=-4.0)

            # real latents
            with torch.no_grad():
                zq, _, _ = codec.encode(mel)

            B = zq.shape[0]

            # conditioning
            cond = cond_cache[:B]
            uncond = uncond_cache[:B]

            # sample one of 2 student times
            idx = torch.randint(0, 2, (B,), device=args.device)
            t = t_student[idx]  # [B]

            noise = torch.randn_like(zq)
            x = zq + t.view(-1, 1, 1) * noise

            # teacher preds
            with torch.no_grad():
                pred_u = teacher(x, t, uncond)
                pred_c = teacher(x, t, cond)

                if args.cfg_collapse:
                    # per-sample guidance (dropout + dynamic cap)
                    g = torch.full((B,), float(g_epoch), device=args.device)
                    g = belel_guidance_dropout(g, p=args.guidance_dropout_p, min_guidance=args.guidance_min)

                    teacher_target = belel_cfg_mix(
                        pred_uncond=pred_u,
                        pred_cond=pred_c,
                        guidance=g,
                        clamp=args.mix_clamp,
                        dynamic_cap=bool(args.dynamic_cap),
                        cap_k=args.cap_k,
                    )

                    # "strong" collapse target to internalize high guidance without extra inference passes
                    g_strong = torch.full((B,), float(args.guidance_max), device=args.device)
                    g_strong = belel_guidance_dropout(g_strong, p=args.guidance_dropout_p, min_guidance=args.guidance_min)

                    teacher_target_strong = belel_cfg_mix(
                        pred_uncond=pred_u,
                        pred_cond=pred_c,
                        guidance=g_strong,
                        clamp=args.mix_clamp,
                        dynamic_cap=bool(args.dynamic_cap),
                        cap_k=args.cap_k,
                    )
                else:
                    teacher_target = pred_c
                    teacher_target_strong = None

            # student single-pass pred
            student_pred = student(x, t, cond)

            # primary distillation
            loss_distill = F.mse_loss(student_pred, teacher_target)

            if args.cfg_collapse:
                # collapse loss pushes student toward strong-guided behavior in one pass
                loss_collapse = F.mse_loss(student_pred, teacher_target_strong)
                loss = loss_distill + float(args.cfg_weight) * loss_collapse
            else:
                loss_collapse = torch.tensor(0.0, device=args.device)
                loss = loss_distill

            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(student.parameters(), float(args.grad_clip))
            optimizer.step()

            loss_sum += float(loss.item())
            n += 1

            pbar.set_postfix(
                loss=loss_sum / max(n, 1),
                distill=float(loss_distill.item()),
                collapse=float(loss_collapse.item()) if args.cfg_collapse else 0.0,
            )

        torch.save({"state_dict": student.state_dict(), "epoch": ep + 1}, args.out)
        print("Saved:", args.out)

    print("✔ 4 → 2 distillation complete")
    print("Student checkpoint:", args.out)
    if args.cfg_collapse:
        print("✔ Teacher-guided CFG collapse enabled")
        print("  guidance_mode:", args.guidance_mode, "power:", args.guidance_power)
        print("  dynamic_cap:", bool(args.dynamic_cap), "cap_k:", args.cap_k)
        print("  clamp:", args.mix_clamp, "dropout_p:", args.guidance_dropout_p)


if __name__ == "__main__":
    main()
