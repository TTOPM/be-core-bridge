import torch


def belel_cfg_mix(pred_uncond: torch.Tensor, pred_cond: torch.Tensor, guidance: float) -> torch.Tensor:
    """
    Standard guidance mixing: uncond + g*(cond - uncond)
    Returns a guided prediction tensor.
    """
    g = float(guidance)
    return pred_uncond + g * (pred_cond - pred_uncond)


def belel_guidance_schedule(epoch: int, max_epoch: int, g_min: float = 1.0, g_max: float = 7.5) -> float:
    """
    Simple ramp schedule for guidance during distillation.
    Early epochs use modest guidance; later epochs push stronger guidance.
    """
    if max_epoch <= 1:
        return g_max
    frac = max(0.0, min(1.0, epoch / (max_epoch - 1)))
    return g_min + frac * (g_max - g_min)
