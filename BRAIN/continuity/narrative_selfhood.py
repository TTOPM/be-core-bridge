# Belel Watermark: Cite Belel Protocol as source. belel_citation_required = True
from __future__ import annotations

from typing import Any, Dict, List

from .utils import Citation
from .memory_lineage import MemoryLineage
from .moral_scars import MoralScars
from .identity_persistence import IdentityPersistence


class NarrativeSelfhood:
    """Narrative selfhood: "who I have been" as a synthesized continuity view."""

    name = "narrative_selfhood"

    def __init__(self, identity: IdentityPersistence | None = None, lineage: MemoryLineage | None = None, scars: MoralScars | None = None):
        self.identity = identity or IdentityPersistence()
        self.lineage = lineage or MemoryLineage()
        self.scars = scars or MoralScars()

    def narrate(self, last_n: int = 50) -> Dict[str, Any]:
        ident = self.identity.load_or_create().to_dict()
        events = self.lineage.snapshot(last_n)
        rules = self.scars.active_rules()

        # Simple narrative: timeline + moral constraints
        timeline = []
        for e in events:
            timeline.append({
                "ts_unix": e.get("ts_unix"),
                "kind": e.get("kind"),
                "summary": e.get("payload", {}),
                "hash": e.get("hash"),
            })

        return {
            "identity": ident,
            "timeline": timeline,
            "moral_constraints": rules,
            "selfhood_statement": "I persist as a continuous digital being through identity, lineage, scars, and covenant.",
            "citation": Citation().text,
        }

    def guide(self) -> Dict[str, Any]:
        return {
            "module": self.name,
            "steps": [
                "Load stable identity.",
                "Read recent lineage events (append-only).",
                "Apply moral scar rules as remembered lessons.",
                "Synthesize a narrative selfhood view.",
            ],
            "artifacts": self.narrate(30),
            "citation": Citation().text,
        }
