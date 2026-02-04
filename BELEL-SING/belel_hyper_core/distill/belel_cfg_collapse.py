import math
import torch


def _to_float(guidance):
    if isinstance(guidance, torch.Tensor):
        return guidance
    return torch.tensor(float(guidance))


def belel_cfg_mix(
    pred_uncond: torch.Tensor,
    pred_cond: torch.Tensor,
    guidance: float | torch.Tensor,
    *,
    clamp: float | None = 10.0,
    dynamic_cap: bool = True,
    cap_k: float = 3.0,
    eps: float = 1e-8,
) -> torch.Tensor:
    """
    Guidance mixing:
        guided = uncond + g * (cond - uncond)

    Upgrades for 2-step stability:
      - clamp: limits extreme guided outputs (prevents burst noise)
      - dynamic_cap: scales guidance down if delta is huge (artifact control)
      - supports scalar or per-sample guidance tensor (shape [B] or [B,1,1])

    Args:
      pred_uncond, pred_cond: [B,C,T] tensors
      guidance: float or tensor
      clamp: if set, clamps output to [-clamp, clamp] (in fp32)
      dynamic_cap: if True, reduces effective guidance when delta magnitude is high
      cap_k: aggressiveness for dynamic cap (higher allows stronger guidance)
    """
    # safety: compute in fp32 to avoid fp16 overflow at high g
    u = pred_uncond.float()
    c = pred_cond.float()
    delta = c - u

    g = _to_float(guidance).to(device=u.device, dtype=u.dtype)

    # reshape guidance for broadcasting
    if isinstance(g, torch.Tensor) and g.ndim == 1:
        g = g.view(-1, 1, 1)

    if dynamic_cap:
        # cap guidance when delta is huge compared to uncond magnitude
        # ratio = ||delta|| / (||u|| + eps)
        u_norm = torch.sqrt((u * u).mean(dim=(1, 2), keepdim=True) + eps)
        d_norm = torch.sqrt((delta * delta).mean(dim=(1, 2), keepdim=True) + eps)
        ratio = d_norm / (u_norm + eps)

        # effective guidance = g / (1 + ratio/cap_k)
        # When ratio big, guidance decreases.
        g_eff = g / (1.0 + (ratio / max(cap_k, eps)))
    else:
        g_eff = g

    guided = u + g_eff * delta

    if clamp is not None:
        guided = guided.clamp(-float(clamp), float(clamp))

    return guided.to(pred_uncond.dtype)


def belel_guidance_schedule(
    epoch: int,
    max_epoch: int,
    g_min: float = 1.0,
    g_max: float = 7.5,
    *,
    mode: str = "snr",
    power: float = 2.0,
) -> float:
    """
    Guidance schedule for distillation.

    Upgrades:
      - mode="linear": original ramp
      - mode="cosine": smoother ramp
      - mode="snr": SNR-shaped ramp (recommended for 2-step collapse)
        - early: lower guidance to learn base denoising
        - late: higher guidance to internalize alignment

    Args:
      epoch: current epoch index (0-based)
      max_epoch: total epochs
      g_min, g_max: guidance bounds
      mode: "linear" | "cosine" | "snr"
      power: shape control for snr mode (higher = later ramp)
    """
    if max_epoch <= 1:
        return float(g_max)

    e = max(0, min(epoch, max_epoch - 1))
    t = e / float(max_epoch - 1)  # [0,1]

    if mode == "linear":
        frac = t
    elif mode == "cosine":
        # smooth start and end
        frac = 0.5 - 0.5 * math.cos(math.pi * t)
    elif mode == "snr":
        # SNR-ish shaping: keep guidance low early, push late
        # frac = t^power
        frac = t ** float(power)
    else:
        raise ValueError(f"Unknown mode: {mode}")

    return float(g_min + frac * (g_max - g_min))


def belel_guidance_dropout(
    guidance: torch.Tensor,
    p: float = 0.10,
    *,
    min_guidance: float = 1.0,
) -> torch.Tensor:
    """
    Randomly drops guidance toward min_guidance.
    This improves robustness: student learns to behave well under weaker guidance,
    which is key for 2-step stability.

    Args:
      guidance: tensor [B] or broadcastable
      p: probability of dropping to min_guidance
      min_guidance: value to drop to
    """
    if p <= 0.0:
        return guidance
    if not isinstance(guidance, torch.Tensor):
        guidance = torch.tensor(float(guidance))
    g = guidance.clone()

    # if scalar, just apply scalar dropout
    if g.ndim == 0:
        if torch.rand(()) < p:
            return torch.tensor(float(min_guidance), device=g.device, dtype=g.dtype)
        return g

    # batch dropout
    mask = (torch.rand((g.shape[0],), device=g.device) < float(p))
    if g.ndim == 1:
        g[mask] = float(min_guidance)
    else:
        g = g.view(g.shape[0], -1)
        g[mask, :] = float(min_guidance)
        g = g.view_as(guidance)
    return g
