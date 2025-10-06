
import torch, torch.nn as nn
class GPTSemanticEncoder(nn.Module):
    def __init__(self, d_model=512):
        super().__init__()
        self.emb = nn.Embedding(10000, d_model)
        self.tr = nn.TransformerEncoder(nn.TransformerEncoderLayer(d_model,8,batch_first=True), num_layers=4)
        self.pitch_proj = nn.Linear(1, d_model)
    def forward(self, text_tokens, melody_f0):
        x = self.emb(text_tokens.clamp_min(0).clamp_max(9999))
        p = self.pitch_proj(melody_f0.float().unsqueeze(-1))
        return self.tr(x+p)
