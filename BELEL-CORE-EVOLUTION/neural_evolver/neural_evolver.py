"""
neural_evolver/neural_evolver.py

Torch-based NAS hook (with a safe fallback if torch is unavailable).

Public API:
    neural_fitness(genome) -> float
"""

from __future__ import annotations

from typing import List

Genome = List[int]


def _decode_arch(genome: Genome) -> List[int]:
    # Map integers to layer widths (kept simple and stable).
    # Widths in [16, 256] roughly.
    widths = []
    for g in genome[:8]:  # cap for sanity
        w = 16 + (int(g) % 16) * 16
        widths.append(w)
    if not widths:
        widths = [64, 64]
    return widths


def neural_fitness(genome: Genome) -> float:
    """
    Returns a proxy fitness score.

    If torch exists, we build a tiny MLP and score it with a deterministic proxy.
    This keeps the pipeline runnable while you wire real datasets later.
    """
    widths = _decode_arch(genome)

    try:
        import torch
        import torch.nn as nn

        layers = []
        in_dim = 32
        for w in widths:
            layers.append(nn.Linear(in_dim, w))
            layers.append(nn.ReLU())
            in_dim = w
        layers.append(nn.Linear(in_dim, 10))
        model = nn.Sequential(*layers)

        # Deterministic proxy: parameter efficiency + mild depth bonus
        n_params = sum(p.numel() for p in model.parameters())
        depth = len(widths)
        score = (depth * 10.0) + (50_000.0 / (n_params + 1.0))
        return float(score)

    except Exception:
        # Fallback: depth + width diversity proxy
        uniq = len(set(widths))
        score = float(len(widths) * 10 + uniq * 3)
        return score
