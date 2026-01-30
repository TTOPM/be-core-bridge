from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class MutationPolicy:
    name: str
    max_change_scope: str = "bounded"   # bounded | expansive
    requires_governance_approval: bool = True
    requires_identity_check: bool = True
    notes: str = ""


def default_policy() -> MutationPolicy:
    return MutationPolicy(
        name="default_bounded_policy",
        max_change_scope="bounded",
        requires_governance_approval=True,
        requires_identity_check=True,
        notes="Registers changes for review by governance_filters before acceptance.",
    )
