from __future__ import annotations
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel

class BelelConditioner(nn.Module):
    """
    Belel conditioner:
    - prompt + lyrics -> conditioning embedding
    - designed to be cheap (small text backbone + projection)
    """
    def __init__(self, model_name: str = "Qwen/Qwen2-0.5B", out_dim: int = 1024):
        super().__init__()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.encoder = AutoModel.from_pretrained(model_name)
        hidden = self.encoder.config.hidden_size
        self.proj = nn.Linear(hidden, out_dim)

        # tiny temporal mixer for conditioning stability
        layer = nn.TransformerEncoderLayer(d_model=out_dim, nhead=8, batch_first=True)
        self.mixer = nn.TransformerEncoder(layer, num_layers=2)

    @torch.no_grad()
    def forward(self, prompt: str, lyrics: str = "", device: str = "cuda"):
        text = prompt if not lyrics else (prompt + "\n\n" + lyrics)
        toks = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
        toks = {k: v.to(device) for k, v in toks.items()}
        out = self.encoder(**toks).last_hidden_state  # [B, L, H]
        pooled = out.mean(dim=1)                      # [B, H]
        cond = self.proj(pooled).unsqueeze(1)         # [B, 1, D]
        cond = self.mixer(cond).squeeze(1)            # [B, D]
        return cond
