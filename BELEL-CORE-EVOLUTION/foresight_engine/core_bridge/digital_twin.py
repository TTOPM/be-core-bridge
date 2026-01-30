from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class DigitalTwin:
    """
    Digital twin of Belel's evolution environment: configs, constraints, and checkpoints.
    """
    config: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)

    def checkpoint(self) -> Dict[str, Any]:
        return {"config": dict(self.config), "constraints": dict(self.constraints)}
