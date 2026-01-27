"""
Gospel Veto Adapter
===================

This adapter reads the existing `gospel_integrity_manifest.yml` from the
repository and applies pattern-based veto checks on input text. It does not
modify the manifest and simply exposes the evaluation result as a data
structure describing whether the text passes the veto, along with any
matching hard-block and soft-flag test names.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import yaml


@dataclass(frozen=True)
class VetoDecision:
    """Represents the result of a veto evaluation."""

    allowed: bool
    hard_blocks: List[str]
    soft_flags: List[str]


class GospelVetoAdapter:
    """Adapter for performing gospel veto checks based on a YAML manifest."""

    def __init__(self, manifest_path: str) -> None:
        # Load the YAML manifest from the provided path
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                self.manifest: Dict[str, Any] = yaml.safe_load(f) or {}
        except FileNotFoundError:
            # If the manifest is missing, default to empty structure
            self.manifest = {}

    def evaluate(self, text: str) -> VetoDecision:
        """Evaluate the given text against the veto patterns in the manifest.

        Args:
            text: The input text to evaluate.

        Returns:
            VetoDecision: The result including lists of matching hard-block and soft-flag tests.
        """
        t = text.lower()
        hard_blocks: List[str] = []
        soft_flags: List[str] = []

        gi = self.manifest.get("gospel_integrity", {})
        veto_tests: Dict[str, Dict[str, Any]] = gi.get("veto_tests", {}) or {}

        for test_name, spec in veto_tests.items():
            patterns = [str(p).lower() for p in (spec.get("pattern", []) or [])]
            severity = str(spec.get("severity", "soft")).lower()
            if any(p in t for p in patterns):
                if severity == "hard":
                    hard_blocks.append(test_name)
                else:
                    soft_flags.append(test_name)

        return VetoDecision(allowed=(len(hard_blocks) == 0), hard_blocks=hard_blocks, soft_flags=soft_flags)