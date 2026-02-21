from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..constants import DEFAULT_KL_TOLERANCE

JSON = Dict[str, Any]


@dataclass(frozen=True)
class SovereignConfig:
    """
    SOVEREIGN-CONFIG
    Governance schema with entropy bounds (KL tolerance) and Concordium gating flags.
    """
    classification: str
    concordium_gated: bool
    kl_tolerance: float = DEFAULT_KL_TOLERANCE
    entropy_bounds: Optional[JSON] = None
    multiversal_bridge_ready: bool = True

    @staticmethod
    def from_json(data: JSON) -> "SovereignConfig":
        return SovereignConfig(
            classification=str(data.get("classification", "Sovereign – Concordium-Gated")),
            concordium_gated=bool(data.get("concordium_gated", True)),
            kl_tolerance=float(data.get("kl_tolerance", DEFAULT_KL_TOLERANCE)),
            entropy_bounds=data.get("entropy_bounds"),
            multiversal_bridge_ready=bool(data.get("multiversal_bridge_ready", True)),
        )


def load_config(path: str) -> SovereignConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return SovereignConfig.from_json(data)