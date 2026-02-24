cat > BELEL-SING/hybrid_svs/shallow_diffusion.py << 'EOF'
from __future__ import annotations

import math
from dataclasses import dataclass

import torch
import torch.nn as nn


@dataclass(frozen=True)
class DiffCfg:
    n_mels: int = 80
    d_model: int = 384
    steps: int = 20


class TimeEmbedding(nn.Module):
    def __init__(self, d: int):
        super().__init__()
        self.d = d
        self.mlp = nn.Sequential(nn.Linear(d, d * 4), nn.SiLU(), nn.Linear(d * 4, d))

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        # t: [B] in [0, steps-1]
        half = self.d // 2
        freqs = torch.exp(-math.log(10000.0) * torch.arange(0, half, device=t.device) / half)
        ang = t.float().unsqueeze(1) * freqs.unsqueeze(0)
        emb = torch.cat([torch.sin(ang), torch.cos(ang)], dim=1)
        if emb.size(1) < self.d:
            emb = torch.cat([emb, torch.zeros((emb.size(0), self.d - emb.size(1)), device=t.device)], dim=1)
        return self.mlp(emb)


class ResBlock(nn.Module):
    def __init__(self, ch: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.GroupNorm(8, ch),
            nn.SiLU(),
            nn.Conv1d(ch, ch, 3, padding=1),
            nn.GroupNorm(8, ch),
            nn.SiLU(),
            nn.Conv1d(ch, ch, 3, padding=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + 0.5 * self.net(x)


class ShallowDiffusionLayer(nn.Module):
    """
    Denoises mel frames with a small diffusion-style network.
    Inputs:
      mel_noisy: [B, T, M]
      cond:      [B, T, D] (semantic encoder output)
      t:         [B] diffusion step
    Output:
      mel_denoised: [B, T, M]
    """
    def __init__(self, cfg: DiffCfg):
        super().__init__()
        self.cfg = cfg
        self.t_emb = TimeEmbedding(cfg.d_model)
        self.cond_proj = nn.Linear(cfg.d_model, cfg.d_model)
        self.in_proj = nn.Conv1d(cfg.n_mels + cfg.d_model, cfg.d_model, 1)
        self.blocks = nn.Sequential(ResBlock(cfg.d_model), ResBlock(cfg.d_model), ResBlock(cfg.d_model))
        self.out_proj = nn.Conv1d(cfg.d_model, cfg.n_mels, 1)

    def forward(self, mel_noisy: torch.Tensor, cond: torch.Tensor, t: torch.Tensor) -> torch.Tensor:
        B, T, M = mel_noisy.shape
        c = self.cond_proj(cond)  # [B, T, D]
        te = self.t_emb(t).unsqueeze(1).expand(B, T, self.cfg.d_model)  # [B,T,D]
        c = c + te

        x = torch.cat([mel_noisy, c], dim=-1)  # [B,T,M+D]
        x = x.transpose(1, 2)  # [B, M+D, T]
        h = self.in_proj(x)
        h = self.blocks(h)
        y = self.out_proj(h).transpose(1, 2)  # [B,T,M]
        return y
EOF