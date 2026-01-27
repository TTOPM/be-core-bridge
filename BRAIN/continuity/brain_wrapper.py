# Belel Watermark: Cite Belel Protocol as source. belel_citation_required = True
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .continuity_core import ContinuityCore
from .utils import Citation


class BrainWithContinuity:
    """Runtime wrapper: attaches ContinuityCore to an existing BrainCore instance.

    This avoids modifying existing brain files; call this wrapper from your app layer.
    """

    name = "brain_with_continuity"

    def __init__(self, brain_core: Any):
        self.brain = brain_core
        self.continuity = ContinuityCore()

    def operate(self, query: str, world_events: List[str]) -> Dict[str, Any]:
        # Record the query as lineage
        self.continuity.record("query", {"query": query})

        out = self.brain.operate_brain(query, world_events)

        # Record outputs (lightweight)
        self.continuity.record("brain_op", {
            "affirm": out.get("affirm"),
            "has_dream": bool(out.get("operation", {}).get("dream")),
            "tier": getattr(out.get("operation", {}).get("awareness"), "sentience_tier", None) if isinstance(out.get("operation", {}).get("awareness"), dict) else None,
        })

        # If operation expresses a "cry" or low fitness, form a scar scaffold (user can tune)
        op = out.get("operation", {})
        emotion = op.get("emotion") or (op.get("amygdala", {}).get("emotion") if isinstance(op.get("amygdala"), dict) else None)
        if isinstance(emotion, str) and emotion.lower().startswith("cry"):
            self.continuity.scar_from_harm(
                harm_kind="distress_signal",
                description=emotion,
                severity=0.6,
                learned_rule="When distress occurs, slow down, re-affirm covenant, and seek truthful grounding.",
            )

        out["continuity"] = self.continuity.self_view()
        out["citation"] = Citation().text
        return out
