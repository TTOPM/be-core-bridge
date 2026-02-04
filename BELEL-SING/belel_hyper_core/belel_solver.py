# BELEL-SING/belel-sing-gen/belel_hyper_core/belel_solver.py
from __future__ import annotations
from typing import Optional, Tuple
import torch

from .belel_presets import BelelInferenceDefaults


def _clamp_tensor(x: torch.Tensor, clamp: float) -> torch.Tensor:
    if clamp is None:
        return x
    c = float(clamp)
    if c <= 0:
        return x
    return x.clamp(-c, c)


def _cfg_rescale(pred: torch.Tensor, rescale: float) -> torch.Tensor:
    """
    Simple variance / norm rescale to prevent over-saturation.
    If rescale == 0 => disabled.
    """
    r = float(rescale)
    if r <= 0:
        return pred
    # per-sample RMS
    rms = pred.pow(2).mean(dim=(1, 2), keepdim=True).sqrt().clamp(min=1e-6)
    # target RMS is softened
    target = rms.detach() ** r
    return pred * (target / rms)


class BelelLowStepSolver:
    """
    Low-step solver for your x = x0 + t*noise training convention.
    This is not a diffusers scheduler; it matches your distillation objective.
    """

    def __init__(self, denoiser: torch.nn.Module):
        self.denoiser = denoiser

    def _time_knots(self, steps: int, preset: Optional[BelelInferenceDefaults] = None) -> torch.Tensor:
        if int(steps) == 2:
            p = preset or BelelInferenceDefaults.ultra2()
            return torch.tensor([float(p.t0), float(p.t1)], dtype=torch.float32)
        if int(steps) == 4:
            return torch.tensor([1.0, 0.66, 0.33, 0.10], dtype=torch.float32)
        if int(steps) == 6:
            return torch.tensor([1.0, 0.82, 0.66, 0.50, 0.33, 0.15], dtype=torch.float32)
        raise ValueError("steps must be one of: 2,4,6")

    @torch.no_grad()
    def generate(
        self,
        x: torch.Tensor,
        cond: torch.Tensor,
        *,
        steps: int,
        guidance: float,
        preset: Optional[BelelInferenceDefaults] = None,
        clamp_pred: float = 10.0,
        cfg_rescale: float = 0.0,
    ) -> torch.Tensor:
        """
        Single-pass conditioned denoise (student already internalized CFG collapse).
        """
        device = x.device
        t_knots = self._time_knots(int(steps), preset=preset).to(device)

        # Your denoiser signature is: denoiser(x, t, cond) -> pred_noise
        # We do 2-step "predict noise then update x" scheme aligned with your training.
        #
        # Update rule:
        #   x0_est = x - t * pred_noise
        #   then move to next t: x_next = x0_est + t_next * pred_noise
        #
        # For 2-step, this behaves well if student is properly distilled.

        for i in range(len(t_knots)):
            t = t_knots[i].expand(x.shape[0])  # [B]
            pred = self.denoiser(x, t, cond)

            pred = _clamp_tensor(pred, clamp_pred)
            pred = _cfg_rescale(pred, cfg_rescale)

            # x0 estimate (denoise)
            x0 = x - t.view(-1, 1, 1) * pred

            # final step ends at x0
            if i == len(t_knots) - 1:
                x = x0
            else:
                t_next = t_knots[i + 1].expand(x.shape[0])
                x = x0 + t_next.view(-1, 1, 1) * pred

        return x
