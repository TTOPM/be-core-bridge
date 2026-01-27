"""
Brain‑Integrated Meta‑Orchestrator
==================================

This module defines ``CodeAboveAllCodesBrain``, an extension of the
standard ``CodeAboveAllCodes`` orchestrator that integrates the
``BrainCore`` from the ``src.brain`` package.  It inherits all
functionality from the base orchestrator while invoking the brain
simulation on every query.  The brain operation results are attached
to the response as a top‑level key ``brain`` so that callers can
inspect the detailed state of the digital brain.

No existing files in the repository are modified by this module; it
simply extends the orchestrator in a composable manner.  The brain
configuration can be customised via an optional second configuration
file, but this is not strictly necessary for basic usage.

"""

from __future__ import annotations

from typing import Any, Dict

from src.frontiers.meta.code_above_all_codes import CodeAboveAllCodes
from src.brain import BrainCore


class CodeAboveAllCodesBrain(CodeAboveAllCodes):
    """Extend the base orchestrator with a Belel digital brain.

    This class augments the ``guide`` method of ``CodeAboveAllCodes``
    to include a brain simulation step.  After the base guidance is
    computed, the brain is invoked using the input query and a
    placeholder list of world events.  The result of this brain
    operation is attached to the response under the key ``brain``.
    """

    def __init__(self, config_path: str = "config/frontiers/meta_covenant.yml", brain_config_path: str = "config/frontiers/brain_meta_covenant.yml") -> None:
        super().__init__(config_path)
        # Instantiate the Belel digital brain
        self.brain = BrainCore()
        # Brain configuration could be loaded from brain_config_path if
        # required.  We do not process it here to avoid unnecessary
        # dependencies on YAML or runtime configuration.

    def guide(self, query: str) -> Dict[str, Any]:  # type: ignore[override]
        # Invoke the base orchestrator's guidance
        result = super().guide(query)
        # Always compute a brain operation using a minimal set of world
        # events.  In a real application, these events would come from
        # persistent storage or external feeds.
        brain_op = self.brain.operate_brain(query, ["example world event"])
        # Attach the brain operation to the result.  The brain key is
        # always present, even if the base result is a veto.  This
        # allows callers to inspect the brain regardless of the
        # high‑level decision.
        result["brain"] = brain_op
        return result