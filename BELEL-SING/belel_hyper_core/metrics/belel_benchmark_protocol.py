# BELEL-SING/belel-sing-gen/belel_hyper_core/metrics/belel_benchmark_protocol.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple
import math

import torch
import torch.nn.functional as F


# ============================================================
# Configuration (locked defaults)
# ============================================================

@dataclass
class BelelBenchmarkGates:
    """
    Hard quality gates.
    If ANY gate fails → output is rejected.
    These can be tightened over time, never loosened.
    """

    # Spectral stability
    max_logmel_l2: float = 0.085

    # High-frequency energy sanity (anti-smear / anti-mush)
    min_hf_energy_ratio: float = 0.015

    # Temporal coherence (frame-to-frame stability)
    max_frame_delta: float = 0.12

    # Voicing stability proxy
    min_voiced_ratio: float = 0.35

    # Lyric / semantic alignment proxy
    min_alignment_score: float = 0.55


@dataclass
class BelelBenchmarkWeights:
    """
    Weights for final scalar score.
    Must sum to 1.0.
    """

    fidelity: float = 0.30
    hf_stability: float = 0.15
    temporal_coherence: float = 0.15
    voicing: float = 0.15
    alignment: float = 0.25


# ============================================================
# Core protocol
# ============================================================

class BelelBenchmarkProtocol:
    """
    Canonical Belel quality judge.

    Inputs:
      - mel: [80, T] float32
      - optional alignment score (0..1) from Belel aligner

    Outputs:
      - final_score: float (0..10)
      - passed: bool
      - breakdown: dict (for logging / evolution)
    """

    def __init__(
        self,
        *,
        gates: BelelBenchmarkGates | None = None,
        weights: BelelBenchmarkWeights | None = None,
    ):
        self.gates = gates or BelelBenchmarkGates()
        self.weights = weights or BelelBenchmarkWeights()

        # Validate weights
        wsum = sum(asdict(self.weights).values())
        if abs(wsum - 1.0) > 1e-6:
            raise ValueError(f"Benchmark weights must sum to 1.0 (got {wsum})")

    # --------------------------------------------------------
    # Public entrypoint
    # --------------------------------------------------------

    def evaluate(
        self,
        mel: torch.Tensor,
        *,
        alignment_score: float = 0.0,
    ) -> Tuple[float, bool, Dict[str, Any]]:
        """
        Evaluate a mel spectrogram.

        Returns:
          score_10: float in [0,10]
          passed: bool
          breakdown: dict
        """
        mel = self._ensure_mel(mel)

        # --- Compute metrics
        logmel_l2 = self._logmel_l2(mel)
        hf_ratio = self._hf_energy_ratio(mel)
        frame_delta = self._temporal_delta(mel)
        voiced_ratio = self._voiced_ratio(mel)

        # --- Gate checks
        gate_failures = {}

        if logmel_l2 > self.gates.max_logmel_l2:
            gate_failures["logmel_l2"] = logmel_l2

        if hf_ratio < self.gates.min_hf_energy_ratio:
            gate_failures["hf_energy_ratio"] = hf_ratio

        if frame_delta > self.gates.max_frame_delta:
            gate_failures["frame_delta"] = frame_delta

        if voiced_ratio < self.gates.min_voiced_ratio:
            gate_failures["voiced_ratio"] = voiced_ratio

        if alignment_score < self.gates.min_alignment_score:
            gate_failures["alignment_score"] = alignment_score

        passed = len(gate_failures) == 0

        # --- Normalize components to 0..1
        fidelity_n = self._inv_norm(logmel_l2, self.gates.max_logmel_l2)
        hf_n = self._norm(hf_ratio, self.gates.min_hf_energy_ratio)
        temporal_n = self._inv_norm(frame_delta, self.gates.max_frame_delta)
        voicing_n = self._norm(voiced_ratio, self.gates.min_voiced_ratio)
        align_n = max(0.0, min(1.0, float(alignment_score)))

        # --- Weighted final score (0..1)
        score_01 = (
            self.weights.fidelity * fidelity_n
            + self.weights.hf_stability * hf_n
            + self.weights.temporal_coherence * temporal_n
            + self.weights.voicing * voicing_n
            + self.weights.alignment * align_n
        )

        score_10 = float(max(0.0, min(10.0, score_01 * 10.0)))

        breakdown = {
            "passed": passed,
            "gate_failures": gate_failures,
            "components": {
                "logmel_l2": logmel_l2,
                "hf_energy_ratio": hf_ratio,
                "frame_delta": frame_delta,
                "voiced_ratio": voiced_ratio,
                "alignment_score": alignment_score,
            },
            "normalized": {
                "fidelity": fidelity_n,
                "hf_stability": hf_n,
                "temporal": temporal_n,
                "voicing": voicing_n,
                "alignment": align_n,
            },
            "weights": asdict(self.weights),
            "gates": asdict(self.gates),
            "score_10": score_10,
        }

        return score_10, passed, breakdown

    # ========================================================
    # Metric implementations (Belel-owned, local)
    # ========================================================

    def _ensure_mel(self, mel: torch.Tensor) -> torch.Tensor:
        if mel.ndim != 2 or mel.shape[0] != 80:
            raise ValueError(f"Expected mel [80,T], got {tuple(mel.shape)}")
        return mel.float()

    def _logmel_l2(self, mel: torch.Tensor) -> float:
        """
        Measures global log-mel energy deviation.
        Lower is better.
        """
        m = mel - mel.mean(dim=1, keepdim=True)
        return float(torch.mean(m.pow(2)).sqrt().item())

    def _hf_energy_ratio(self, mel: torch.Tensor) -> float:
        """
        High-frequency energy / total energy.
        Prevents over-smoothing.
        """
        hf = mel[60:, :]
        num = torch.mean(hf.abs())
        den = torch.mean(mel.abs()) + 1e-6
        return float((num / den).item())

    def _temporal_delta(self, mel: torch.Tensor) -> float:
        """
        Frame-to-frame instability proxy.
        """
        d = mel[:, 1:] - mel[:, :-1]
        return float(torch.mean(d.abs()).item())

    def _voiced_ratio(self, mel: torch.Tensor) -> float:
        """
        Rough voiced/unvoiced proxy using energy thresholding.
        """
        energy = mel.mean(dim=0)
        thr = energy.mean() * 0.5
        voiced = (energy > thr).float().mean()
        return float(voiced.item())

    # ========================================================
    # Normalization helpers
    # ========================================================

    @staticmethod
    def _norm(x: float, ref: float) -> float:
        if ref <= 0:
            return 0.0
        return max(0.0, min(1.0, x / ref))

    @staticmethod
    def _inv_norm(x: float, ref: float) -> float:
        if ref <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - (x / ref)))
