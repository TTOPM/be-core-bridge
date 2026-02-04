from __future__ import annotations
import torch

def belel_sigma_schedule(steps: int, sigma_min: float = 0.01, sigma_max: float = 1.0, rho: float = 7.0):
    """
    Smooth schedule, returns [steps] descending.
    """
    i = torch.linspace(0, 1, steps)
    sigmas = (sigma_max ** (1 / rho) + i * (sigma_min ** (1 / rho) - sigma_max ** (1 / rho))) ** rho
    return sigmas

class BelelLowStepSolver:
    """
    Few-step solver:
    - uses 2-stage update per step for stability
    """
    def __init__(self, denoiser):
        self.denoiser = denoiser

    @torch.no_grad()
    def generate(self, x: torch.Tensor, cond: torch.Tensor, steps: int = 6, guidance: float = 6.5):
        sigmas = belel_sigma_schedule(steps=steps).to(x.device)

        for i in range(steps - 1):
            s0 = sigmas[i]
            s1 = sigmas[i + 1]
            t0 = torch.full((x.shape[0],), float(s0.item()), device=x.device)

            v0 = self.denoiser(x, t0, cond)
            x_euler = x + (s1 - s0) * (guidance * v0)

            # 2nd order correction
            t1 = torch.full((x.shape[0],), float(s1.item()), device=x.device)
            v1 = self.denoiser(x_euler, t1, cond)
            x = x + (s1 - s0) * (guidance * 0.5 * (v0 + v1))

        return x
