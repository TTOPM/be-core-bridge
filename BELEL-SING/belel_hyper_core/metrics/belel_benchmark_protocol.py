# BELEL-SING/belel-sing-gen/belel_hyper_core/metrics/belel_benchmark_protocol.py
from __future__ import annotations

import time
import math
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional

import numpy as np
import torch


# ============================================================
# BENCHMARK RESULT
# ============================================================

@dataclass
class BelelBenchmarkResult:
    # Performance
    wall_time_sec: float
    peak_vram_gb: float

    # Audio fidelity proxies
    spectral_convergence: float
    hf_energy_stability: float
    transient_stability: float

    # Vocal / structure proxies
    voiced_ratio_stability: float
    formant_continuity: float
    structural_repetition_penalty: float

    # Composite
    quality_score: float
    passed: bool

    details: Dict[str, Any]


# ============================================================
# PROTOCOL DEFAULTS (LOCKED GATES)
# ============================================================

@dataclass
class BelelBenchmarkGates:
    """
    These are not arbitrary.
    They define what BELEL considers acceptable output.
    """

    # Performance (RTX 4090 class expectations)
    max_wall_time_sec: float = 6.0
    max_peak_vram_gb: float = 18.0

    # Fidelity
    max_spectral_convergence: float = 0.18     # lower is better
    min_hf_energy_stability: float = 0.85       # higher is better
    min_transient_stability: float = 0.80

    # Vocal / structure
    min_voiced_ratio_stability: float = 0.75
    min_formant_continuity: float = 0.78
    max_structural_repetition_penalty: float = 0.25

    # Composite score
    min_quality_score: float = 8.2


# ============================================================
# CORE METRICS
# ============================================================

def _spectral_convergence(mel: torch.Tensor) -> float:
    """
    Measures frame-to-frame spectral drift.
    Lower = more stable / less smear.
    """
    diff = mel[:, 1:] - mel[:, :-1]
    num = diff.norm(p=2)
    den = mel.norm(p=2).clamp(min=1e-6)
    return float((num / den).clamp(0, 1).item())


def _hf_energy_stability(mel: torch.Tensor) -> float:
    """
    High-frequency energy consistency proxy.
    """
    hf = mel[int(mel.shape[0] * 0.65) :, :]
    energy = hf.abs().mean(dim=0)
    std = energy.std()
    mean = energy.mean().clamp(min=1e-6)
    stability = 1.0 - (std / mean).clamp(0, 1)
    return float(stability.item())


def _transient_stability(mel: torch.Tensor) -> float:
    """
    Penalizes excessive transient spikes (clicks, zipper noise).
    """
    delta = mel[:, 1:] - mel[:, :-1]
    spikes = (delta.abs() > 3.5).float().mean()
    return float((1.0 - spikes).clamp(0, 1).item())


def _voiced_ratio_stability(mel: torch.Tensor) -> float:
    """
    Simple voiced/unvoiced proxy using energy floor.
    """
    energy = mel.mean(dim=0)
    voiced = (energy > energy.mean() * 0.6).float()
    ratio = voiced.mean()
    return float((1.0 - abs(ratio - 0.55)).clamp(0, 1).item())


def _formant_continuity(mel: torch.Tensor) -> float:
    """
    Penalizes erratic spectral centroid jumps.
    """
    freqs = torch.arange(mel.shape[0], device=mel.device).float()
    centroid = (mel * freqs[:, None]).sum(dim=0) / mel.sum(dim=0).clamp(min=1e-6)
    jumps = (centroid[1
