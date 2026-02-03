from mamba_ssm import Mamba
import torch

class SSMEnhancer(torch.nn.Module):
    def __init__(self, d_model=1024):
        super().__init__()
        self.mamba = Mamba(d_model=d_model, d_state=64, d_conv=8, expand=4)

    def enhance_sequence(self, embeds):
        # Efficient long-seq for music tokens
        return self.mamba(embeds)  # Linear scaling

# Use in main: melody_embeds = SSMEnhancer()(melody_tokens)
