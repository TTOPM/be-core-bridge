from __future__ import annotations
import torch
import torch.nn as nn

class FiniteScalarQuantization(nn.Module):
    """
    Belel FSQ:
    - per-channel scalar quantization with configurable levels
    - supports straight-through estimator for training
    """
    def __init__(self, levels: list[int], straight_through: bool = True):
        super().__init__()
        if not levels or any(l <= 1 for l in levels):
            raise ValueError("levels must be a list of ints > 1")
        self.register_buffer("_levels", torch.tensor(levels, dtype=torch.float32), persistent=False)
        self.straight_through = straight_through

    def forward(self, z: torch.Tensor):
        """
        z: [B, C, T] assumed roughly normalized to [-1, 1]
        returns:
          zq: [B, C, T] quantized to [-1, 1]
          codes: [B, C, T] int codes in [0, level-1]
          commit_loss: scalar tensor (0 if straight-through only)
        """
        if z.ndim != 3:
            raise ValueError("z must be [B, C, T]")

        B, C, T = z.shape
        device = z.device

        # Tile levels to channels if needed
        levels = self._levels.to(device)
        if levels.numel() != C:
            reps = (C + levels.numel() - 1) // levels.numel()
            levels = levels.repeat(reps)[:C]
        levels = levels.view(1, C, 1)

        z_clamped = z.clamp(-1.0, 1.0)
        scaled = (z_clamped + 1.0) * 0.5  # [0,1]
        # codes in [0, L-1]
        codes = torch.floor(scaled * levels).to(torch.int32).clamp(min=0, max=(levels - 1).to(torch.int32))

        denom = (levels - 1.0).clamp_min(1.0)
        zq = (codes.to(torch.float32) / denom) * 2.0 - 1.0

        # straight-through: pass gradients as if identity
        if self.straight_through and z.requires_grad:
            zq = z_clamped + (zq - z_clamped).detach()

        commit_loss = torch.zeros((), device=device)
        return zq, codes, commit_loss


class BelelDeepCompressor(nn.Module):
    """
    Belel deep compression autoencoder:
    mel: [B, mel_bins, T] -> latent: [B, latent_ch, T/4] -> recon mel
    """
    def __init__(
        self,
        mel_bins: int = 128,
        latent_ch: int = 32,
        hidden: int = 512,
        fsq_levels: list[int] | None = None,
        straight_through: bool = True,
    ):
        super().__init__()
        self.mel_bins = mel_bins
        self.latent_ch = latent_ch

        self.encoder = nn.Sequential(
            nn.Conv1d(mel_bins, hidden, kernel_size=5, stride=2, padding=2),
            nn.SiLU(),
            nn.Conv1d(hidden, hidden, kernel_size=5, stride=2, padding=2),
            nn.SiLU(),
            nn.Conv1d(hidden, latent_ch, kernel_size=3, stride=1, padding=1),
        )

        fsq_levels = fsq_levels or [8, 8, 8, 8, 8, 8, 8, 8]
        self.quantizer = FiniteScalarQuantization(levels=fsq_levels, straight_through=straight_through)

        self.decoder = nn.Sequential(
            nn.ConvTranspose1d(latent_ch, hidden, kernel_size=4, stride=2, padding=1),
            nn.SiLU(),
            nn.ConvTranspose1d(hidden, hidden, kernel_size=4, stride=2, padding=1),
            nn.SiLU(),
            nn.Conv1d(hidden, mel_bins, kernel_size=3, stride=1, padding=1),
        )

    def encode(self, mel: torch.Tensor):
        if mel.ndim != 3:
            raise ValueError("mel must be [B, mel_bins, T]")
        z = self.encoder(mel)
        zq, codes, commit_loss = self.quantizer(z.tanh())
        return zq, codes, commit_loss

    def decode(self, zq: torch.Tensor):
        return self.decoder(zq)

    def forward(self, mel: torch.Tensor):
        zq, codes, commit_loss = self.encode(mel)
        recon = self.decode(zq)
        return recon, codes, zq, commit_loss
