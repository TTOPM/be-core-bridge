
import torch, torch.nn as nn, torch.nn.functional as F
from .semantic_encoder import GPTSemanticEncoder
from .shallow_diffusion import ShallowDiffusionLayer
from .f0_extractor import RMVPEF0Extractor

class HiFiGANVocoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.gen = nn.Sequential(
            nn.ConvTranspose1d(80,256,16,stride=4,padding=6), nn.ReLU(),
            nn.ConvTranspose1d(256,64,16,stride=4,padding=6), nn.ReLU(),
            nn.ConvTranspose1d(64,1,16,stride=4,padding=6)
        )
    def forward(self, mel): return torch.tanh(self.gen(mel).squeeze(1))

class TransformerDecoder(nn.Module):
    def __init__(self, d_model=512, n_layers=6):
        super().__init__()
        self.layers = nn.ModuleList([nn.TransformerDecoderLayer(d_model,8,batch_first=True) for _ in range(n_layers)])
        self.proj = nn.Linear(d_model,80)
    def forward(self, x):
        for l in self.layers: x = l(x,x)
        return self.proj(x).transpose(1,2)

class HybridSVS(nn.Module):
    def __init__(self, cfg):
        super().__init__()
        self.cfg=cfg
        d = cfg.get("d_model",512)
        self.enc = GPTSemanticEncoder(d)
        self.dec = TransformerDecoder(d, cfg.get("num_layers",6))
        self.diff = ShallowDiffusionLayer(cfg.get("diffusion_steps",50), d)
        self.voc = HiFiGANVocoder()
        self.f0ext = RMVPEF0Extractor(cfg.get("sample_rate",24000))
        self.vib_hz = nn.Parameter(torch.tensor(5.0)); self.vib_amt = nn.Parameter(torch.tensor(0.02))
    def forward(self, text_tokens, melody_f0, ref_audio=None, controls=None):
        T = melody_f0.size(1); sr=self.cfg.get("sample_rate",24000); hop=self.cfg.get("hop_length",256)
        t = torch.arange(T, device=melody_f0.device).float()*(hop/sr)
        vib = self.vib_amt*torch.sin(2*torch.pi*self.vib_hz*t)
        m = melody_f0 + vib
        h = self.enc(text_tokens, m)
        mel = self.dec(h)                  # [B,80,T]
        mel = self.diff(mel.transpose(1,2)).transpose(1,2)
        wav = self.voc(mel)
        return wav, mel

def vibrato_loss(pred_f0, gt_f0):
    l1 = F.l1_loss(pred_f0, gt_f0)
    return l1
