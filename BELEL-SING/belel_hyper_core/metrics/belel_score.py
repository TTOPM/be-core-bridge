from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, Tuple
import math

from .belel_audio_metrics import BelelAudioMetrics


@dataclass
class BelelScoreConfig:
    # weights sum does not need to equal 1
    w_no_clipping: float = 2.0
    w_rms: float = 1.0
    w_dc: float = 0.5
    w_flatness: float = 1.0
    w_centroid: float = 0.75
    w_stability: float = 1.5
    w_zcr: float = 0.5
    w_duration: float = 1.0

    # target ranges / preferences
    # (tune later using your benchmark listening + stats)
    rms_target: float = 0.12
    rms_tol: float = 0.10

    centroid_target_hz: float = 2400.0
    centroid_tol_hz: float = 2200.0

    flatness_target: float = 0.12
    flatness_tol: float = 0.20

    zcr_target: float = 0.08
    zcr_tol: float = 0.10

    dc_tol: float = 0.03

    # expected duration range
    duration_min_sec: float = 2.0
    duration_max_sec: float = 1200.0  # 20 minutes


def _gaussian_score(x: float, mu: float, tol: float) -> float:
    tol = max(1e-8, float(tol))
    z = (float(x) - float(mu)) / tol
    return float(math.exp(-0.5 * z * z))


def _clamp01(x: float) -> float:
    return float(max(0.0, min(1.0, float(x))))


def belel_auto_score(metrics: BelelAudioMetrics, cfg: Optional[BelelScoreConfig] = None) -> Tuple[float, Dict[str, Any]]:
    """
    Returns:
      score_0_to_10, breakdown dict
    This is a *local heuristic score* designed for evolution ranking, not a paper benchmark.
    """
    cfg = cfg or BelelScoreConfig()

    # 1) No clipping: higher is better
    s_clip = _clamp01(1.0 - (metrics.clip_frac * 12.0))  # clip_frac 0.08 -> ~0
    # 2) RMS in a sane loudness band
    s_rms = _gaussian_score(metrics.rms, cfg.rms_target, cfg.rms_tol)
    # 3) DC near zero
    s_dc = _clamp01(1.0 - (abs(metrics.dc_offset) / max(1e-8, cfg.dc_tol)))
    # 4) Flatness (too flat = noisy, too peaky = dull) -> target a “musical” band
    s_flat = _gaussian_score(metrics.spec_flatness, cfg.flatness_target, cfg.flatness_tol)
    # 5) Centroid (avoid muffled or harsh)
    s_cent = _gaussian_score(metrics.spec_centroid_hz, cfg.centroid_target_hz, cfg.centroid_tol_hz)
    # 6) Energy stability proxy
    s_stab = _clamp01(metrics.energy_stability)
    # 7) ZCR proxy (extreme ZCR often correlates with noise)
    s_zcr = _gaussian_score(metrics.zcr, cfg.zcr_target, cfg.zcr_tol)

    # 8) Duration sanity
    s_dur = 1.0 if (cfg.duration_min_sec <= metrics.duration_sec <= cfg.duration_max_sec) else 0.0

    # weighted sum -> normalize to 0..1
    wsum = (
        cfg.w_no_clipping + cfg.w_rms + cfg.w_dc + cfg.w_flatness +
        cfg.w_centroid + cfg.w_stability + cfg.w_zcr + cfg.w_duration
    )
    if wsum <= 0:
        wsum = 1.0

    score01 = (
        cfg.w_no_clipping * s_clip +
        cfg.w_rms * s_rms +
        cfg.w_dc * s_dc +
        cfg.w_flatness * s_flat +
        cfg.w_centroid * s_cent +
        cfg.w_stability * s_stab +
        cfg.w_zcr * s_zcr +
        cfg.w_duration * s_dur
    ) / wsum

    score10 = float(max(0.0, min(10.0, 10.0 * score01)))

    breakdown = {
        "score01": score01,
        "score10": score10,
        "components": {
            "no_clipping": s_clip,
            "rms": s_rms,
            "dc": s_dc,
            "flatness": s_flat,
            "centroid": s_cent,
            "stability": s_stab,
            "zcr": s_zcr,
            "duration": s_dur,
        },
        "weights": asdict(cfg),
        "metrics": metrics.to_dict(),
    }
    return score10, breakdown
