from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class WorldModel:
    """
    Lightweight world model: stores state snapshots and simple transitions.
    This is the hook-point for the future digital-twin + forecasting stack.
    """
    state: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def observe(self, obs: Dict[str, Any]) -> None:
        self.state.update(obs)
        self.history.append(dict(self.state))

    def predict_next(self) -> Dict[str, Any]:
        # Minimal: returns current state as next prediction placeholder.
        return dict(self.state)
