from __future__ import annotations
import torch
import torch.nn as nn
from transformers import AutoTokenizer, AutoModel

class BelelConditioner(nn.Module):
    """
    Belel conditioner:
    prompt + lyrics -> cond embedding [B, D]
    """
    def __init__(self, model_name: str = "Qwen/Qwen2-0.5B", embed_dim: int = 1024):
        super().__init__()
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.text_encoder = AutoModel.from_pretrained(model_name)

        hidden = int(self.text_encoder.config.hidden_size)
        self.proj = nn.Linear(hidden, embed_dim)

        layer = nn.TransformerEncoderLayer(d_model=embed_dim, nhead=8, batch_first=True)
        self.mixer = nn.TransformerEncoder(layer, num_layers=2)

    @torch.no_grad()
    def forward(self, text_prompt: str, lyrics: str = "", device: str = "cuda"):
        text = text_prompt if not lyrics else f"{text_prompt}\n\n{lyrics}"
        toks = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
        toks = {k: v.to(device) for k, v in toks.items()}
        out = self.text_encoder(**toks).last_hidden_state  # [1, L, H]
        pooled = out.mean(dim=1)                           # [1, H]
        cond = self.proj(pooled).unsqueeze(1)              # [1, 1, D]
        cond = self.mixer(cond).squeeze(1)                 # [1, D]
        return cond
