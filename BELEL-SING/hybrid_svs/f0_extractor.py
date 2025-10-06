
import torch
class RMVPEF0Extractor:
    def __init__(self, sample_rate=24000, hop_length=256): self.sr=sample_rate; self.hop=hop_length
    def __call__(self, wav): # [B, samples]
        B = wav.size(0); T = max(int(wav.size(1)/(self.sr/self.hop)), 200)
        return torch.zeros(B,T, device=wav.device)
