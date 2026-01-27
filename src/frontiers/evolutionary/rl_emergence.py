"""
Reinforcement Learning Emergence Module
======================================

This module contains a minimal reinforcement learning (RL) component used
by the Belel frontiers expansion. It defines a simple policy network that
maps a state vector to an action value, along with an `evolve` method to
update the policy based on a reward signal. Although rudimentary, this
component provides a hook for future expansion into more sophisticated
evolutionary or RL strategies.

If PyTorch is unavailable in the environment, the module falls back to
applying a simple proportional update to the action value without any
learned parameters. This ensures that the rest of the system can still
function without external dependencies.
"""

from __future__ import annotations

from typing import Any
import random


class RLEmergence:
    """A minimal reinforcement learning engine for evolutionary updates."""

    def __init__(self) -> None:
        # Attempt to initialise a linear policy network if torch is available.
        try:
            import torch  # type: ignore
            import torch.nn as nn  # type: ignore
            import torch.optim as optim  # type: ignore
            self.use_torch = True
            self.policy: Any = nn.Linear(10, 1)
            self.optim: Any = optim.SGD(self.policy.parameters(), lr=0.01)
        except Exception:
            self.use_torch = False
            self.policy = None
            self.optim = None

    def evolve(self, state: list[float], reward: float) -> float:
        """Update the policy with a state and reward and return the action.

        Args:
            state: A list of floats representing the current state features.
            reward: A reward signal, typically between 0 and 1.

        Returns:
            float: The action value produced by the policy after the update.
        """
        if self.use_torch and self.policy is not None:
            import torch  # type: ignore
            import torch.nn.functional as F  # type: ignore
            # Convert state to tensor
            s = torch.tensor([state], dtype=torch.float32)
            action = self.policy(s)
            # Policy gradient: encourage actions proportional to reward
            loss = -reward * action.mean()
            self.optim.zero_grad()
            loss.backward()
            self.optim.step()
            # Clamp action to [0, 1]
            value = float(torch.sigmoid(action).item())
        else:
            # Fallback: adjust the first element toward the reward
            if state:
                value = state[0] + (reward - state[0]) * 0.1
            else:
                value = reward * 0.1
            value = max(0.0, min(value, 1.0))
        return value