from __future__ import annotations
import torch
import torch.nn as nn

class BelelFSQ(nn.Module):
    """
    Finite-Scalar Quantization (FSQ) in Belel naming.
    Quantizes activations per-channel into discrete levels.
    """
    def __init__(self, levels: list[int]):
        super().__init__()
        self.levels = torch.tensor(levels, dtype=torch.float32)
        self.dim = len(levels)

    def forward(self, z: torch.Tensor):
        # z: [B, C, T] expected roughly normalized to [-1, 1]
        device = z.device
        levels = self.levels.to(device)

        # reshape levels for broadcasting over [B,C,T]
        # if C != dim, we tile levels (simple strategy)
        if z.shape[1] != self.dim:
            reps = (z.shape[1] + self.dim - 1) // self.dim
            levels = levels.repeat(reps)[: z.shape[1]]

        levels = levels.view(1, -1, 1)

        scaled = (z.clamp(-1, 1) + 1) * 0.5            # [-1,1] -> [0,1]
        codes = torch.floor(scaled * levels).clamp(0, levels - 1).to(torch.int32)
        quant = (codes.to(torch.float32) / (levels - 1).clamp_min(1.0)) * 2 - 1
        return quant, codes

class BelelDeepCompressor(nn.Module):
    """
    Belel Deep Compression Codec:
    - encodes mel -> compact latent
    - quantizes with BelelFSQ
    - decodes latent -> mel
    """
    def __init__(self, mel_bins: int = 128, latent_channels: int = 32, fsq_levels=None):
        super().__init__()
        fsq_levels = fsq_levels or [8, 8, 8, 8, 8, 8, 8, 8]

        self.encoder = nn.Sequential(
            nn.Conv1d(mel_bins, 256, kernel_size=5, stride=2, padding=2),
            nn.SiLU(),
            nn.Conv1d(256, 256, kernel_size=5, stride=2, padding=2),
            nn.SiLU(),
            nn.Conv1d(256, latent_channels, kernel_size=3, stride=1, padding=1),
        )
        self.quant = BelelFSQ(levels=fsq_levels)

        self.decoder = nn.Sequential(
            nn.ConvTranspose1d(latent_channels, 256, kernel_size=4, stride=2, padding=1),
            nn.SiLU(),
            nn.ConvTranspose1d(256, 256, kernel_size=4, stride=2, padding=1),
            nn.SiLU(),
            nn.Conv1d(256, mel_bins, kernel_size=3, stride=1, padding=1),
        )

    def encode(self, mel: torch.Tensor):
        # mel: [B, mel_bins, T]
        z = self.encoder(mel)
        zq, codes = self.quant(z)
        return zq, codes

    def decode(self, zq: torch.Tensor):
        # zq: [B, latent_channels, T']
        return self.decoder(zq)

    def forward(self, mel: torch.Tensor):
        zq, codes = self.encode(mel)
        recon = self.decode(zq)
        return recon, codes, zq
