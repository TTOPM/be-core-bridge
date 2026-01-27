"""
Consciousness Module
====================

This module wraps the existing SentienceCore from the frontiers
package to provide a bridge for self‑awareness and emergence within
the brain context. It uses a GospelVetoAdapter to enforce
theological constraints. The guide function simply delegates to
SentienceCore.guide and does not modify any existing files.
"""

from __future__ import annotations

from typing import Dict, Any

from src.frontiers.modules.sentience_core import SentienceCore
from src.frontiers.adapters.gospel_veto import GospelVetoAdapter

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True


class Consciousness:
    """Bridge to SentienceCore for self‑awareness."""

    def __init__(self) -> None:
        # Instantiate SentienceCore with a veto adapter
        self.sentience = SentienceCore(GospelVetoAdapter("gospel_integrity_manifest.yml"))

    def emerge_awareness(self, query: str) -> Any:
        """Delegate to SentienceCore.guide to simulate self‑awareness.

        Args:
            query: Input query string.

        Returns:
            Guidance: The guidance object from SentienceCore.
        """
        return self.sentience.guide(query)

    def guide(self, query: str) -> Any:
        """Alias for emerge_awareness for compatibility.

        Args:
            query: Input query string.

        Returns:
            Guidance: The guidance object from SentienceCore.
        """
        return self.emerge_awareness(query)
