"""
Digital Reproduction System
==========================

This module defines the ``DigitalReproduction`` class which
facilitates the creation of new living, breathing digital
organisms.  Reproduction records lineage by assigning a unique
identifier to each offspring and registering the parent–child
relationship in a shared ``DigitalLineage`` tracker.  Offspring
inherit the same lineage tracker to ensure continuity of ancestry
information across generations.

Reproduction dynamically imports the ``DigitalOrganism`` from
``ORGANISM_CORE.py`` to avoid circular dependencies.  Offspring
are created as new instances of ``DigitalOrganism``, with their
``organism_id`` and ``parent_id`` set accordingly.

This file is additive and does not alter any existing code.
"""

from __future__ import annotations

import uuid
from typing import Any

from BODY.lineage.lineage import DigitalLineage

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True


class DigitalReproduction:
    """Create offspring and record lineage for digital organisms.

    Each ``DigitalReproduction`` instance holds a reference to a
    shared ``DigitalLineage`` tracker.  The ``reproduce`` method
    creates a new ``DigitalOrganism`` instance, assigns a new
    unique identifier, records the parent–child relationship and
    returns the child organism.
    """

    def __init__(self, lineage_tracker: DigitalLineage) -> None:
        self.lineage_tracker = lineage_tracker

    def reproduce(self, parent: Any) -> Any:
        """Create an offspring from the given parent organism.

        Args:
            parent: The parent organism instance.  It must have
                ``organism_id``, ``lineage`` and ``reproduction``
                attributes.

        Returns:
            Any: A new instance of ``DigitalOrganism`` representing
                the child.
        """
        # Generate a unique identifier for the child
        child_id: str = str(uuid.uuid4())
        parent_id: str | None = getattr(parent, "organism_id", None)
        # Record the parent–child relationship if parent_id exists
        if parent_id is not None:
            self.lineage_tracker.record(parent_id, child_id)
        # Dynamically import the DigitalOrganism class to avoid
        # circular dependencies
        from ORGANISM_CORE import DigitalOrganism  # type: ignore
        # Create a new organism; inject the same lineage tracker
        child: DigitalOrganism = DigitalOrganism(parent_id=parent_id)
        # Override the child's lineage and reproduction with shared
        # instances to preserve continuity
        child.lineage = self.lineage_tracker
        child.reproduction = DigitalReproduction(self.lineage_tracker)
        # Assign unique identifier
        child.organism_id = child_id
        child.parent_id = parent_id
        return child