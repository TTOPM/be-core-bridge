# BELEL-SING/belel-sing-gen/belel_hyper_core/belel_editing.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any

import torch


@dataclass
class BelelEditSpec:
    """
    Defines an edit region in latent/mel time.

    You operate in LATENT time (x shape [B,C,T_latent]) for repaint/retake,
    because solver runs there. Engine will convert seconds->frames->latent_T.

    start_t, end_t are inclusive/exclusive indices in latent time.
    """
    start_t: int
    end_t: int

    # strength in [0..1]:
    # 0 => minimal change, 1 => full regen inside region
    strength: float = 1.0

    # feather controls soften boundary artifacts
    feather: int = 8


def _clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(int(x), int(hi)))


def _make_soft_mask(T: int, start: int, end: int, feather: int, device: torch.device) -> torch.Tensor:
    """
    Creates a soft 1D mask of shape [1,1,T] with 1 inside [start,end) and
    smooth ramps of length `feather` on both sides.
    """
    start = _clamp_int(start, 0, T)
    end = _clamp_int(end, 0, T)
    if end <= start:
        m = torch.zeros((1, 1, T), device=device)
        return m

    m = torch.zeros((T,), device=device, dtype=torch.float32)

    m[start:end] = 1.0

    f = int(max(0, feather))
    if f > 0:
        # left ramp
        ls0 = max(0, start - f)
        ls1 = start
        if ls1 > ls0:
            ramp = torch.linspace(0.0, 1.0, steps=(ls1 - ls0), device=device)
            m[ls0:ls1] = torch.maximum(m[ls0:ls1], ramp)

        # right ramp
        rs0 = end
        rs1 = min(T, end + f)
        if rs1 > rs0:
            ramp = torch.linspace(1.0, 0.0, steps=(rs1 - rs0), device=device)
            m[rs0:rs1] = torch.maximum(m[rs0:rs1], ramp)

    return m.view(1, 1, T)


def apply_repaint_update(
    x_prev: torch.Tensor,
    x_new: torch.Tensor,
    mask_1d: torch.Tensor,
) -> torch.Tensor:
    """
    Blend old/new in latent space using mask_1d [1,1,T] or [B,1,T].
    """
    if mask_1d.ndim == 3:
        m = mask_1d
    else:
        raise ValueError("mask_1d must be [B,1,T] or [1,1,T]")

    if m.shape[0] == 1 and x_prev.shape[0] > 1:
        m = m.expand(x_prev.shape[0], -1, -1)

    # expand to [B,C,T]
    m = m.expand(x_prev.shape[0], x_prev.shape[1], x_prev.shape[2])
    return x_prev * (1.0 - m) + x_new * m


@torch.no_grad()
def repaint_latent(
    solver_generate_fn,
    *,
    x_init: torch.Tensor,
    cond: torch.Tensor,
    steps: int,
    guidance: float,
    clamp_pred: float,
    cfg_rescale: float,
    edit: BelelEditSpec,
    preset: Optional[Any] = None,
    seed: Optional[int] = None,
) -> Tuple[torch.Tensor, Dict[str, Any]]:
    """
    Generic repaint in latent space.

    solver_generate_fn signature MUST be:
        x_out = solver_generate_fn(x, cond, steps=..., guidance=..., preset=..., clamp_pred=..., cfg_rescale=...)

    Strategy:
      1) Create a stochastic variant x_noise inside region (controlled by strength)
      2) Run solver from that mixed x
      3) Blend back into original with a soft mask

    This works for:
      - retake: edit region, strength=1
      - lyric edit: call with new cond (from new lyrics) + region mask
      - repaint: same cond, different seed/strength
    """
    device = x_init.device
    B, C, T = x_init.shape

    start = _clamp_int(edit.start_t, 0, T)
    end = _clamp_int(edit.end_t, 0, T)
    feather = int(max(0, edit.feather))
    strength = float(max(0.0, min(1.0, edit.strength)))

    mask = _make_soft_mask(T, start, end, feather, device=device)

    # new noise inside region
    if seed is not None:
        torch.manual_seed(int(seed))
        if device.type == "cuda":
            try:
                torch.cuda.manual_seed_all(int(seed))
            except Exception:
                pass

    noise = torch.randn_like(x_init)

    # mix: outside region keep x_init; inside region interpolate to noise-driven x
    # "strength" controls how much we perturb the region before regeneration
    x_mixed = x_init + (noise * strength)

    # Generate full latent (fast, then we blend only region)
    x_gen = solver_generate_fn(
        x_mixed,
        cond,
        steps=int(steps),
        guidance=float(guidance),
        preset=preset,
        clamp_pred=float(clamp_pred),
        cfg_rescale=float(cfg_rescale),
    )

    x_out = apply_repaint_update(x_prev=x_init, x_new=x_gen, mask_1d=mask)

    meta = {
        "edit_mode": "repaint",
        "edit_start_t": int(start),
        "edit_end_t": int(end),
        "edit_strength": float(strength),
        "edit_feather": int(feather),
    }
    return x_out, meta


def seconds_to_latent_range(
    *,
    start_sec: float,
    end_sec: float,
    duration_sec: float,
    latent_T: int,
) -> Tuple[int, int]:
    """
    Map seconds into latent indices [0..latent_T).
    """
    dur = float(max(1e-6, duration_sec))
    s0 = float(max(0.0, min(dur, start_sec)))
    s1 = float(max(0.0, min(dur, end_sec)))
    if s1 < s0:
        s0, s1 = s1, s0
    i0 = int(round((s0 / dur) * latent_T))
    i1 = int(round((s1 / dur) * latent_T))
    i0 = max(0, min(latent_T, i0))
    i1 = max(0, min(latent_T, i1))
    if i1 <= i0:
        i1 = min(latent_T, i0 + 1)
    return i0, i1
