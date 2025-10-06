
import torch, torch.nn as nn
class ShallowDiffusionLayer(nn.Module):
    def __init__(self, steps=50, d_model=512):
        super().__init__()
        self.block = nn.Sequential(nn.Conv1d(80,80,3,padding=1), nn.ReLU(), nn.Conv1d(80,80,3,padding=1))
    def forward(self, mel_t): # [B,T,80]
        x = mel_t.transpose(1,2)
        return self.block(x).transpose(1,2)
