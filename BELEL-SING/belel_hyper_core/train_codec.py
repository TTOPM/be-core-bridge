from __future__ import annotations
import os
from dataclasses import dataclass
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

from belel_hyper_core.belel_latent_codec import BelelDeepCompressor

@dataclass
class BelelCodecTrainConfig:
    device: str = "cuda"
    lr: float = 2e-4
    batch_size: int = 8
    steps: int = 20000
    save_every: int = 1000
    out_dir: str = "checkpoints/belel_codec"
    mel_bins: int = 128
    latent_ch: int = 32

class BelelMelDataset(Dataset):
    """
    Minimal dataset contract:
    - expects .pt files each containing a tensor [mel_bins, T]
    You can export these from your existing Belel mel pipeline.
    """
    def __init__(self, root: str):
        self.root = root
        self.files = [os.path.join(root, f) for f in os.listdir(root) if f.endswith(".pt")]
        if not self.files:
            raise RuntimeError(f"No .pt mel tensors found in: {root}")

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):
        x = torch.load(self.files[idx], map_location="cpu")  # [mel_bins, T]
        if x.ndim != 2:
            raise ValueError("Expected [mel_bins, T]")
        return x

def _pad_collate(batch):
    # batch: list of [M, T]
    M = batch[0].shape[0]
    T = max(x.shape[1] for x in batch)
    out = torch.zeros(len(batch), M, T)
    for i, x in enumerate(batch):
        out[i, :, : x.shape[1]] = x
    return out

def main(mel_root: str, cfg: BelelCodecTrainConfig):
    os.makedirs(cfg.out_dir, exist_ok=True)
    ds = BelelMelDataset(mel_root)
    dl = DataLoader(ds, batch_size=cfg.batch_size, shuffle=True, num_workers=2, collate_fn=_pad_collate)

    model = BelelDeepCompressor(mel_bins=cfg.mel_bins, latent_ch=cfg.latent_ch).to(cfg.device)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr)

    step = 0
    model.train()

    while step < cfg.steps:
        for mel in dl:
            mel = mel.to(cfg.device)
            recon, _, _, commit = model(mel)

            # Reconstruction losses
            l1 = (recon - mel).abs().mean()
            l2 = F.mse_loss(recon, mel)
            loss = 0.7 * l1 + 0.3 * l2 + 0.0 * commit

            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()

            step += 1
            if step % 50 == 0:
                print({"step": step, "loss": float(loss.item()), "l1": float(l1.item()), "l2": float(l2.item())})

            if step % cfg.save_every == 0:
                path = os.path.join(cfg.out_dir, f"codec_step_{step}.pt")
                torch.save({"model": model.state_dict(), "cfg": cfg.__dict__}, path)
                print("saved:", path)

            if step >= cfg.steps:
                break

    final_path = os.path.join(cfg.out_dir, "codec_final.pt")
    torch.save({"model": model.state_dict(), "cfg": cfg.__dict__}, final_path)
    print("saved:", final_path)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mel_root", required=True, help="Folder of .pt mel tensors [128, T]")
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--batch", type=int, default=8)
    args = ap.parse_args()

    cfg = BelelCodecTrainConfig(steps=args.steps, batch_size=args.batch)
    main(args.mel_root, cfg)
