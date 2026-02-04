from __future__ import annotations
import os
from dataclasses import dataclass
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

from belel_hyper_core.belel_latent_codec import BelelDeepCompressor
from belel_hyper_core.belel_denoiser import BelelDenoiser1D

@dataclass
class BelelDenoiserTrainConfig:
    device: str = "cuda"
    lr: float = 2e-4
    batch_size: int = 8
    steps: int = 60000
    save_every: int = 2000
    out_dir: str = "checkpoints/belel_denoiser"
    mel_bins: int = 128
    latent_ch: int = 32
    cond_dim: int = 1024
    sigma_min: float = 0.01
    sigma_max: float = 1.0

class BelelMelDataset(Dataset):
    def __init__(self, root: str):
        self.files = [os.path.join(root, f) for f in os.listdir(root) if f.endswith(".pt")]
        if not self.files:
            raise RuntimeError(f"No .pt files found in {root}")

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        x = torch.load(self.files[idx], map_location="cpu")  # [M, T]
        return x

def _pad_collate(batch):
    M = batch[0].shape[0]
    T = max(x.shape[1] for x in batch)
    out = torch.zeros(len(batch), M, T)
    for i, x in enumerate(batch):
        out[i, :, : x.shape[1]] = x
    return out

def sample_sigma(B: int, sigma_min: float, sigma_max: float, device: str):
    # log-uniform is more stable for denoising
    u = torch.rand(B, device=device)
    return sigma_min * (sigma_max / sigma_min) ** u

def main(mel_root: str, codec_ckpt: str, cfg: BelelDenoiserTrainConfig):
    os.makedirs(cfg.out_dir, exist_ok=True)

    ds = BelelMelDataset(mel_root)
    dl = DataLoader(ds, batch_size=cfg.batch_size, shuffle=True, num_workers=2, collate_fn=_pad_collate)

    codec = BelelDeepCompressor(mel_bins=cfg.mel_bins, latent_ch=cfg.latent_ch).to(cfg.device)
    codec.load_state_dict(torch.load(codec_ckpt, map_location="cpu")["model"])
    codec.eval()
    for p in codec.parameters():
        p.requires_grad = False

    denoiser = BelelDenoiser1D(channels=cfg.latent_ch, cond_dim=cfg.cond_dim).to(cfg.device)
    opt = torch.optim.AdamW(denoiser.parameters(), lr=cfg.lr)

    # conditioning: for now, use a learned null embedding; later you replace with your text conditioning
    null_cond = torch.zeros(cfg.batch_size, cfg.cond_dim, device=cfg.device)

    step = 0
    denoiser.train()

    while step < cfg.steps:
        for mel in dl:
            mel = mel.to(cfg.device)
            with torch.no_grad():
                zq, _, _ = codec.encode(mel)  # [B, C, T']

            B = zq.shape[0]
            cond = null_cond[:B]

            sigma = sample_sigma(B, cfg.sigma_min, cfg.sigma_max, cfg.device)  # [B]
            noise = torch.randn_like(zq)
            x = zq + sigma.view(B, 1, 1) * noise

            # Train to predict noise (classic denoise objective)
            pred = denoiser(x, sigma, cond)
            loss = F.mse_loss(pred, noise)

            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(denoiser.parameters(), 1.0)
            opt.step()

            step += 1
            if step % 50 == 0:
                print({"step": step, "loss": float(loss.item())})

            if step % cfg.save_every == 0:
                path = os.path.join(cfg.out_dir, f"denoiser_step_{step}.pt")
                torch.save({"model": denoiser.state_dict(), "cfg": cfg.__dict__}, path)
                print("saved:", path)

            if step >= cfg.steps:
                break

    final_path = os.path.join(cfg.out_dir, "denoiser_final.pt")
    torch.save({"model": denoiser.state_dict(), "cfg": cfg.__dict__}, final_path)
    print("saved:", final_path)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mel_root", required=True)
    ap.add_argument("--codec_ckpt", required=True)
    ap.add_argument("--steps", type=int, default=60000)
    ap.add_argument("--batch", type=int, default=8)
    args = ap.parse_args()

    cfg = BelelDenoiserTrainConfig(steps=args.steps, batch_size=args.batch)
    main(args.mel_root, args.codec_ckpt, cfg)
