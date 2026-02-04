from __future__ import annotations
import math
import torch
import torch.nn as nn

def _sinusoidal_time_emb(t: torch.Tensor, dim: int) -> torch.Tensor:
    """
    t: [B] float in [0,1] or sigma
    returns [B, dim]
    """
    half = dim // 2
    freqs = torch.exp(-math.log(10000) * torch.arange(0, half, device=t.device).float() / max(half - 1, 1))
    args = t[:, None] * freqs[None, :]
    emb = torch.cat([torch.sin(args), torch.cos(args)], dim=-1)
    if dim % 2 == 1:
        emb = torch.cat([emb, torch.zeros_like(emb[:, :1])], dim=-1)
    return emb

class BelelResBlock1D(nn.Module):
    def __init__(self, ch: int, time_dim: int, cond_dim: int):
        super().__init__()
        self.norm1 = nn.GroupNorm(8, ch)
        self.conv1 = nn.Conv1d(ch, ch, 3, padding=1)
        self.norm2 = nn.GroupNorm(8, ch)
        self.conv2 = nn.Conv1d(ch, ch, 3, padding=1)

        self.time_proj = nn.Linear(time_dim, ch)
        self.cond_proj = nn.Linear(cond_dim, ch)

        self.act = nn.SiLU()

    def forward(self, x: torch.Tensor, t_emb: torch.Tensor, c_emb: torch.Tensor):
        # x: [B, C, T]
        h = self.conv1(self.act(self.norm1(x)))
        h = h + self.time_proj(t_emb).unsqueeze(-1) + self.cond_proj(c_emb).unsqueeze(-1)
        h = self.conv2(self.act(self.norm2(h)))
        return x + h

class BelelDenoiser1D(nn.Module):
    """
    Denoiser predicts "velocity" style residual in latent space.
    """
    def __init__(self, channels: int = 32, width: int = 256, depth: int = 8, cond_dim: int = 1024, time_dim: int = 256):
        super().__init__()
        self.time_dim = time_dim
        self.cond_dim = cond_dim

        self.inp = nn.Conv1d(channels, width, 3, padding=1)
        self.blocks = nn.ModuleList([BelelResBlock1D(width, time_dim=time_dim, cond_dim=cond_dim) for _ in range(depth)])
        self.out = nn.Conv1d(width, channels, 3, padding=1)

        self.time_mlp = nn.Sequential(
            nn.Linear(time_dim, time_dim),
            nn.SiLU(),
            nn.Linear(time_dim, time_dim),
        )

    def forward(self, x: torch.Tensor, t: torch.Tensor, cond: torch.Tensor):
        # t: [B] float sigma or normalized step index
        t_emb = _sinusoidal_time_emb(t.float(), self.time_dim)
        t_emb = self.time_mlp(t_emb)

        h = self.inp(x)
        for b in self.blocks:
            h = b(h, t_emb, cond)
        return self.out(h)
