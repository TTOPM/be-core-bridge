cat > BELEL-SING/hybrid_svs/semantic_encoder.py << 'EOF'
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import torch
import torch.nn as nn


@dataclass(frozen=True)
class EncoderCfg:
    vocab_size: int = 512
    d_model: int = 384
    n_heads: int = 6
    n_layers: int = 6
    dropout: float = 0.1


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, dropout: float = 0.1, max_len: int = 4096):
        super().__init__()
        self.dropout = nn.Dropout(dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0), persistent=False)  # [1, max_len, d_model]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, T, D]
        x = x + self.pe[:, : x.size(1), :]
        return self.dropout(x)


class GPTSemanticEncoder(nn.Module):
    """
    Text+melody semantic encoder.
    Inputs:
      text_tokens: [B, T] int64
      melody_f0:   [B, T] float32 Hz at same rate as tokens (planner aligns)
    Output:
      h: [B, T, D]
    """
    def __init__(self, cfg: EncoderCfg):
        super().__init__()
        self.cfg = cfg
        self.emb = nn.Embedding(cfg.vocab_size, cfg.d_model)
        self.pos = PositionalEncoding(cfg.d_model, cfg.dropout)
        self.pitch_proj = nn.Sequential(
            nn.Linear(1, cfg.d_model),
            nn.SiLU(),
            nn.Linear(cfg.d_model, cfg.d_model),
        )
        enc_layer = nn.TransformerEncoderLayer(
            d_model=cfg.d_model,
            nhead=cfg.n_heads,
            dim_feedforward=cfg.d_model * 4,
            dropout=cfg.dropout,
            batch_first=True,
            activation="gelu",
            norm_first=True,
        )
        self.tr = nn.TransformerEncoder(enc_layer, num_layers=cfg.n_layers)
        self.norm = nn.LayerNorm(cfg.d_model)

    def forward(self, text_tokens: torch.Tensor, melody_f0: torch.Tensor) -> torch.Tensor:
        tok = text_tokens.clamp(min=0, max=self.cfg.vocab_size - 1)
        x = self.emb(tok)  # [B, T, D]
        x = self.pos(x)

        # pitch conditioning: log-f0 with 0 treated as unvoiced
        f0 = melody_f0.float().unsqueeze(-1)
        logf0 = torch.where(f0 > 0.0, torch.log(f0.clamp_min(1e-3)), torch.zeros_like(f0))
        p = self.pitch_proj(logf0)
        h = self.tr(x + p)
        return self.norm(h)
EOF