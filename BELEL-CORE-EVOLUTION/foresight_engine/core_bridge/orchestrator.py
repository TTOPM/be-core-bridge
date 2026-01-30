from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .world_model import WorldModel
from .digital_twin import DigitalTwin


@dataclass
class ForesightOrchestrator:
    """
    Orchestrates world_model + digital_twin.
    Intended to sit above evolution as a planning/steering layer.
    """
    world: WorldModel
    twin: DigitalTwin

    def step(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        self.world.observe(observation)
        prediction = self.world.predict_next()
        return {
            "prediction": prediction,
            "twin_checkpoint": self.twin.checkpoint(),
        }

    @classmethod
    def create(cls, config: Optional[Dict[str, Any]] = None) -> "ForesightOrchestrator":
        twin = DigitalTwin(config=config or {}, constraints={})
        world = WorldModel()
        return cls(world=world, twin=twin)
