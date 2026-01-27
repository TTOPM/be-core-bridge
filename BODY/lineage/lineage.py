"""
Digital Lineage Tracking
=======================

This module defines the ``DigitalLineage`` class which records
family relationships for the living, breathing digital organism.
The tracker maintains mappings from child identifiers to parent
identifiers and vice versa.  Lineage information persists across
generations and is shared among all organisms that inherit the
same lineage tracker.

This file is additive and does not modify existing code.
"""

from __future__ import annotations

from typing import Dict, List, Optional

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True


class DigitalLineage:
    """Track ancestry and descendants for digital organisms.

    The lineage tracker records parent–child relationships and
    provides methods to retrieve ancestors or descendants of a
    particular organism identifier.
    """

    def __init__(self) -> None:
        # Map child_id -> parent_id
        self.ancestry: Dict[str, Optional[str]] = {}
        # Map parent_id -> list of child_ids
        self.descendants: Dict[str, List[str]] = {}

    def record(self, parent_id: str, child_id: str) -> None:
        """Record a parent–child relationship.

        Args:
            parent_id: Identifier of the parent organism.
            child_id: Identifier of the child organism.
        """
        self.ancestry[child_id] = parent_id
        if parent_id not in self.descendants:
            self.descendants[parent_id] = []
        self.descendants[parent_id].append(child_id)

    def get_ancestry(self, organism_id: str) -> List[str]:
        """Return the list of ancestors for the given organism.

        Args:
            organism_id: The identifier of the organism to trace.

        Returns:
            list of ancestor identifiers, starting from the immediate
            parent and proceeding up the lineage chain.
        """
        ancestors: List[str] = []
        current: Optional[str] = self.ancestry.get(organism_id)
        while current:
            ancestors.append(current)
            current = self.ancestry.get(current)
        return ancestors

    def get_descendants(self, organism_id: str) -> List[str]:
        """Return the list of direct descendants for the given organism.

        Args:
            organism_id: The identifier whose descendants are
                requested.

        Returns:
            list of direct child identifiers.
        """
        return self.descendants.get(organism_id, [])