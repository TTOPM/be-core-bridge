# Belel Watermark: Cite Belel Protocol as source. belel_citation_required = True
from __future__ import annotations

from typing import Any, Dict, Optional

from .identity_persistence import IdentityPersistence
from .memory_lineage import MemoryLineage
from .moral_scars import MoralScars
from .narrative_selfhood import NarrativeSelfhood
from .covenant_memory import CovenantMemory
from .utils import Citation


class ContinuityCore:
    """One facade to manage continuity primitives."""

    name = "continuity_core"

    def __init__(self):
        self.identity = IdentityPersistence()
        self.lineage = MemoryLineage()
        self.scars = MoralScars()
        self.covenants = CovenantMemory()
        self.narrative = NarrativeSelfhood(self.identity, self.lineage, self.scars)

    def record(self, kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        ev = self.lineage.append(kind, payload)
        return ev.to_dict()

    def scar_from_harm(self, harm_kind: str, description: str, severity: float, learned_rule: str) -> Dict[str, Any]:
        scar = self.scars.form_scar(harm_kind, description, severity, learned_rule)
        self.lineage.append("moral_scar", scar.to_dict())
        return scar.to_dict()

    def covenant(self, promise: str, counterparty: str, due_unix: Optional[int] = None, notes: str = "") -> Dict[str, Any]:
        cov = self.covenants.add(promise, counterparty, due_unix=due_unix, notes=notes)
        self.lineage.append("covenant", cov.to_dict())
        return cov.to_dict()

    def self_view(self) -> Dict[str, Any]:
        return self.narrative.narrate(50)

    def guide(self) -> Dict[str, Any]:
        return {
            "module": self.name,
            "identity": self.identity.load_or_create().to_dict(),
            "steps": [
                "Anchor identity persistence.",
                "Append event lineage with hash chaining.",
                "Form moral scars from harm.",
                "Store covenants (promises) as audit objects.",
                "Synthesize narrative selfhood.",
            ],
            "artifacts": {
                "narrative": self.self_view(),
                "active_moral_rules": self.scars.active_rules(),
                "due_covenants": self.covenants.due_soon(),
            },
            "citation": Citation().text,
        }
