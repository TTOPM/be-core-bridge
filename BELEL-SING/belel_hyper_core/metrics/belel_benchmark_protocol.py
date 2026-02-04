# BELEL-SING/belel-sing-gen/belel_hyper_core/metrics/belel_benchmark_protocol.py
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, Any, Tuple, Optional
import math

import torch


# ============================================================
# Configuration (locked defaults)
# ============================================================

@dataclass
class BelelBenchmarkGates:
    """
    Hard quality + performance gates.
    If ANY gate fails → output is rejected.

    Rule: tighten over time; do not loosen.
    """

    # -------------------------
    # Quality gates (mel-domain)
    # -------------------------

    # Global mel stability / spread proxy
    max_logmel_rms: float = 0.85

    # High-frequency energy sanity (anti-smear / anti-mush)
    min_hf_energy_ratio: float = 0.015

    # Temporal coherence proxy (frame-to-frame change)
    max_frame_delta: float = 0.12

    # Voicing stability proxy (energy thresholding)
    min_voiced_ratio: float = 0.35

    # Lyric / semantic alignment proxy (0..1) external for now
    min_alignment_score: float = 0.55

    # -------------------------
    # Performance gates
    # -------------------------

    # Real-time factor gate (duration / wall_time), bigger is faster
    min_rtf: float = 0.20

    # Peak VRAM gate (GB)
    max_peak_vram_gb: float = 24.0


@dataclass
class BelelBenchmarkWeights:
    """
    Weights for final scalar score.
    Must sum to 1.0.
    """

    fidelity: float = 0.25
    hf_stability: float = 0.15
    temporal_coherence: float = 0.15
    voicing: float = 0.15
    alignment: float = 0.20
    performance: float = 0.10
    vram_efficiency: float = 0.0  # keep 0 until you decide how to weight it


# ============================================================
# Core protocol
# ============================================================

class BelelBenchmarkProtocol:
    """
    Canonical Belel judge.

    Inputs:
      - mel: [80, T] float32
      - alignment_score: float (0..1) from Belel aligner (external for now)
      - duration_sec: int (for RTF scoring)
      - wall_time_sec: float
      - peak_vram_gb: float

    Outputs:
      - score_10: float (0..10)
      - passed: bool
      - breakdown: dict (for logging / evolution)
    """

    def __init__(
        self,
        *,
        gates: Optional[BelelBenchmarkGates] = None,
        weights: Optional[BelelBenchmarkWeights] = None,
    ):
        self.gates = gates or BelelBenchmarkGates()
        self.weights = weights or BelelBenchmarkWeights()

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
        duration_sec: int = 0,
        wall_time_sec: float = 0.0,
        peak_vram_gb: float = 0.0,
    ) -> Tuple[float, bool, Dict[str, Any]]:
        mel = self._ensure_mel(mel)

        # --- Metrics (mel-domain)
        logmel_rms = self._logmel_rms(mel)
        hf_ratio = self._hf_energy_ratio(mel)
        frame_delta = self._temporal_delta(mel)
        voiced_ratio = self._voiced_ratio(mel)

        # --- Performance derived
        rtf = (float(duration_sec) / float(wall_time_sec)) if (duration_sec > 0 and wall_time_sec > 1e-9) else 0.0

        # --- Gate checks
        gate_failures: Dict[str, Any] = {}

        if logmel_rms > self.gates.max_logmel_rms:
            gate_failures["logmel_rms"] = float(logmel_rms)

        if hf_ratio < self.gates.min_hf_energy_ratio:
            gate_failures["hf_energy_ratio"] = float(hf_ratio)

        if frame_delta > self.gates.max_frame_delta:
            gate_failures["frame_delta"] = float(frame_delta)

        if voiced_ratio < self.gates.min_voiced_ratio:
            gate_failures["voiced_ratio"] = float(voiced_ratio)

        if float(alignment_score) < self.gates.min_alignment_score:
            gate_failures["alignment_score"] = float(alignment_score)

        if rtf < self.gates.min_rtf:
            gate_failures["rtf"] = float(rtf)

        if float(peak_vram_gb) > float(self.gates.max_peak_vram_gb):
            gate_failures["peak_vram_gb"] = float(peak_vram_gb)

        passed = len(gate_failures) == 0

        # --- Normalize components to 0..1
        # For "lower is better" metrics, inv_norm is used.
        fidelity_n = self._inv_norm(logmel_rms, self.gates.max_logmel_rms)
        hf_n = self._norm(hf_ratio, self.gates.min_hf_energy_ratio)
        temporal_n = self._inv_norm(frame_delta, self.gates.max_frame_delta)
        voicing_n = self._norm(voiced_ratio, self.gates.min_voiced_ratio)
        align_n = max(0.0, min(1.0, float(alignment_score)))

        # Performance normalization:
        # - score 0 when below min_rtf
        # - approaches 1 as rtf increases (log-style)
        perf_n = self._perf_norm(rtf, min_rtf=float(self.gates.min_rtf))

        # VRAM efficiency (optional; default weight 0)
        vram_n = self._inv_norm(float(peak_vram_gb), float(self.gates.max_peak_vram_gb))

        # --- Weighted final score (0..1)
        score_01 = (
            self.weights.fidelity * fidelity_n
            + self.weights.hf_stability * hf_n
            + self.weights.temporal_coherence * temporal_n
            + self.weights.voicing * voicing_n
            + self.weights.alignment * align_n
            + self.weights.performance * perf_n
            + self.weights.vram_efficiency * vram_n
        )
        score_10 = float(max(0.0, min(10.0, score_01 * 10.0)))

        breakdown = {
            "passed": bool(passed),
            "gate_failures": gate_failures,
            "components": {
                "logmel_rms": float(logmel_rms),
                "hf_energy_ratio": float(hf_ratio),
                "frame_delta": float(frame_delta),
                "voiced_ratio": float(voiced_ratio),
                "alignment_score": float(alignment_score),
                "rtf": float(rtf),
                "peak_vram_gb": float(peak_vram_gb),
            },
            "normalized": {
                "fidelity": float(fidelity_n),
                "hf_stability": float(hf_n),
                "temporal": float(temporal_n),
                "voicing": float(voicing_n),
                "alignment": float(align_n),
                "performance": float(perf_n),
                "vram_efficiency": float(vram_n),
            },
            "weights": asdict(self.weights),
            "gates": asdict(self.gates),
            "score_10": float(score_10),
        }

        return score_10, passed, breakdown

    # ========================================================
    # Metric implementations (Belel-owned, local)
    # ========================================================

    def _ensure_mel(self, mel: torch.Tensor) -> torch.Tensor:
        if not isinstance(mel, torch.Tensor):
            raise TypeError("mel must be a torch.Tensor")
        if mel.ndim != 2 or int(mel.shape[0]) != 80:
            raise ValueError(f"Expected mel [80,T], got {tuple(mel.shape)}")
        return mel.float()

    def _logmel_rms(self, mel: torch.Tensor) -> float:
        """
        Global RMS of mean-centered mel.
        Lower is more stable/less smeared, but too-low can imply over-smoothing.
        This is a proxy, not an oracle.
        """
        m = mel - mel.mean(dim=1, keepdim=True)
        return float(torch.mean(m.pow(2)).sqrt().item())

    def _hf_energy_ratio(self, mel: torch.Tensor) -> float:
        """
        High-frequency energy / total energy.
        Prevents over-smoothing and loss of 'air' / consonants.
        """
        hf = mel[60:, :]
        num = torch.mean(hf.abs())
        den = torch.mean(mel.abs()) + 1e-6
        return float((num / den).item())

    def _temporal_delta(self, mel: torch.Tensor) -> float:
        """
        Frame-to-frame instability proxy.
        Lower means smoother temporal evolution (but too low can indicate mush).
        """
        if mel.shape[1] < 2:
            return 0.0
        d = mel[:, 1:] - mel[:, :-1]
        return float(torch.mean(d.abs()).item())

    def _voiced_ratio(self, mel: torch.Tensor) -> float:
        """
        Rough voiced/unvoiced proxy using energy thresholding.
        This correlates with intelligibility in many mel pipelines.
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
        return max(0.0, min(1.0, float(x) / float(ref)))

    @staticmethod
    def _inv_norm(x: float, ref: float) -> float:
        if ref <= 0:
            return 0.0
        return max(0.0, min(1.0, 1.0 - (float(x) / float(ref))))

    @staticmethod
    def _perf_norm(rtf: float, *, min_rtf: float) -> float:
        """
        Maps RTF to [0..1] with diminishing returns:
          - 0 at/below min_rtf
          - grows log-like beyond that
        """
        r = float(rtf)
        m = float(max(1e-9, min_rtf))
        if r <= m:
            return 0.0
        # log scale: r=m -> 0, r=10m -> ~0.5, r=100m -> ~1 (clamped)
        x = math.log10(r / m)
        return max(0.0, min(1.0, x / 2.0))