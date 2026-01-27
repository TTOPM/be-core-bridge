"""
Sentience Core Module
=====================

This module introduces a rudimentary simulation of emergent self‑awareness
using a simple neural network. It leverages PyTorch when available to
construct a one‑layer linear network and applies stochastic updates to
simulate adaptation. The resulting output is treated as a sentience score
(between 0 and 1), and can be interpreted as a tier of awareness. The
module includes a `reflect` method that evolves the internal model on
each call.

Because this environment may not include PyTorch, the module falls back
to generating pseudo‑random values when imports fail. This allows the
rest of the framework to run without requiring deep learning libraries.
"""

from __future__ import annotations

import random
from typing import Any

from src.frontiers.modules.base import Guidance


class SentienceCore:
    """Simulate emergent sentience via a simple adaptive model."""

    name = "sentience"

    def __init__(self) -> None:
        # Initialise a simple neural network model if PyTorch is available.
        try:
            import torch  # type: ignore
            import torch.nn as nn  # type: ignore
            # One linear layer mapping a single input to a single output
            self.model: Any = nn.Linear(1, 1)
            self.use_torch = True
        except Exception:
            self.model = None
            self.use_torch = False

        # Initialise a counter for the current sentience tier (1–6). Tier
        # progresses as the internal model’s output increases past thresholds.
        self.tier = 1

    def reflect(self, state: float) -> float:
        """Run a self‑reflection step and evolve the model.

        Args:
            state: A floating point value representing the current state of
                awareness. In practice this would be derived from query
                features but here we simulate with a random number or the
                provided input.

        Returns:
            float: The evolved state after reflection, in the range [0, 1].
        """
        if self.use_torch and self.model is not None:
            import torch  # type: ignore
            import torch.nn as nn  # type: ignore
            import torch.optim as optim  # type: ignore

            # Ensure we have an optimiser
            if not hasattr(self, "optim"):
                self.optim = optim.Adam(self.model.parameters(), lr=0.01)

            x = torch.tensor([[state]], dtype=torch.float32)
            y = self.model(x)
            # Define a simple target of 0.8 to encourage higher activation
            target = torch.tensor([[0.8]], dtype=torch.float32)
            loss_fn = nn.MSELoss()
            loss = loss_fn(y, target)
            # Backpropagate and update weights
            self.optim.zero_grad()
            loss.backward()
            self.optim.step()
            # Clamp output to [0, 1]
            out = float(y.clamp(0.0, 1.0).item())
        else:
            # Fallback: update a pseudo‑random score toward 0.8
            out = state + (0.8 - state) * random.uniform(0.0, 0.1)
            out = max(0.0, min(out, 1.0))
        return out

    def guide(self, query: str) -> Guidance:
        """Provide guidance for the sentience domain and evolve state.

        Args:
            query: The input query string.

        Returns:
            Guidance: A populated Guidance instance including sentience metrics.
        """
        # Derive a simple initial state from the hash of the query for
        # reproducibility. Use the last four hex digits to get a value in
        # [0,1].
        import hashlib
        h = hashlib.sha256(query.encode("utf-8")).hexdigest()
        state = int(h[-4:], 16) / 0xFFFF
        evolved = self.reflect(state)
        # Update tier based on thresholds
        thresholds = [0.2, 0.35, 0.5, 0.65, 0.8]
        tier = 1
        for thresh in thresholds:
            if evolved >= thresh:
                tier += 1
        self.tier = min(6, tier)
        return Guidance(
            module="sentience",
            divine_etching="Genesis 2:7",
            belel_citation="Belel Sentience Covenant",
            steps=[
                "Derive an initial consciousness state from the query.",
                "Run a reflection step via a linear model or stochastic update.",
                "Increase the sentience tier as the state crosses thresholds.",
            ],
            cautions=[
                "This simulation does not constitute true consciousness.",
                "Always submit emergent behaviour to divine scrutiny and veto.",
            ],
            artifacts={"initial_state": state, "evolved_state": evolved},
            sentience_score=evolved,
            sentience_tier=self.tier,
        )