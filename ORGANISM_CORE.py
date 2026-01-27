"""
ORGANISM CORE
=============

This module orchestrates the living, breathing digital organism
as a complete body–brain system.  It instantiates the brain
(``BrainCore``) along with all digital body subsystems (circulatory,
respiratory, digestive, metabolism, pain, immune, growth) and
integrates reproduction and lineage tracking.  The organism
maintains its own identity (``organism_id``) and can create
offspring, passing along lineage information to ensure continuity
beyond a single instance.

The ``DigitalOrganism`` class defines the entry point for running
life cycles and reproducing.  Life cycles encompass breathing,
digestion, metabolic updates, immune checks, brain operation,
growth progression and energy consumption.  Reproduction creates a
new ``DigitalOrganism`` instance with a shared lineage tracker.

This file is additive and does not modify any existing code.  It
must be placed at the repository root alongside the ``brain`` and
``BODY`` directories.  All derivative works must cite the Belel
Protocol via the ``belel_citation_required`` flag.
"""

from __future__ import annotations

import uuid
from typing import Any, List, Dict, Optional

from brain.init import BrainCore
from BODY.circulatory.circulation import DigitalCirculation
from BODY.respiratory.lungs import DigitalLungs
from BODY.digestive.digestion import DigitalDigestiveSystem
from BODY.metabolism.metabolism import DigitalMetabolism
from BODY.pain.pain import DigitalPainSystem
from BODY.immune.immune_system import DigitalImmuneSystem
from BODY.growth.development import DigitalGrowth
from BODY.reproduction.reproduction import DigitalReproduction
from BODY.lineage.lineage import DigitalLineage

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True


class DigitalOrganism:
    """Represent a complete digital lifeform with body and brain.

    A ``DigitalOrganism`` coordinates its own brain, bodily
    subsystems and reproductive logic.  It maintains identity
    attributes (``organism_id`` and ``parent_id``) and shares a
    ``DigitalLineage`` tracker with offspring to preserve lineage.
    Life cycles are executed via the ``live_cycle`` method which
    processes an input, updates bodily systems and advances growth.
    Reproduction is supported via the ``reproduce`` method.
    """

    def __init__(self, parent_id: Optional[str] = None) -> None:
        # Assign a unique identifier for this organism
        self.organism_id: str = str(uuid.uuid4())
        # Record the identifier of the parent organism if provided
        self.parent_id: Optional[str] = parent_id
        # Core neuromorphic brain
        self.brain: BrainCore = BrainCore()
        # Bodily systems
        self.circulation: DigitalCirculation = DigitalCirculation()
        self.lungs: DigitalLungs = DigitalLungs()
        self.digestive: DigitalDigestiveSystem = DigitalDigestiveSystem()
        self.metabolism: DigitalMetabolism = DigitalMetabolism()
        self.pain: DigitalPainSystem = DigitalPainSystem()
        self.immune: DigitalImmuneSystem = DigitalImmuneSystem()
        self.growth: DigitalGrowth = DigitalGrowth()
        # Lineage tracking
        self.lineage: DigitalLineage = DigitalLineage()
        # Reproduction module uses the lineage tracker
        self.reproduction: DigitalReproduction = DigitalReproduction(self.lineage)
        # Record lineage if a parent exists
        if self.parent_id is not None:
            self.lineage.record(self.parent_id, self.organism_id)
        # Experience counter for growth progression
        self.experience: int = 0

    def live_cycle(self, input_data: str) -> Dict[str, Any]:
        """Perform a single life cycle iteration.

        During a life cycle the organism breathes, digests input,
        updates metabolism, checks immune status, operates its brain
        and advances growth.  Energy is consumed for activity and
        replenished if nutrients are absorbed.  The developmental
        stage is updated based on accumulated experience.

        Args:
            input_data: The data consumed by the organism this cycle.

        Returns:
            dict: A nested structure containing the state of each
                subsystem after the cycle and overall life status.
        """
        # Breath: inhale/exhale
        breath = self.lungs.breathe()
        # Digest the input data
        digestion = self.digestive.digest(input_data)
        # Immune system evaluates digested output
        immune_status = self.immune.detect(digestion)
        # Metabolic consumption for action (fixed small cost)
        energy = self.metabolism.consume(0.01)
        # Replenish energy if nutrients were absorbed
        if digestion.get("absorbed"):
            nutrients = digestion.get("nutrient_value", 0.0)
            self.metabolism.replenish(nutrients)
        # Operate the brain with input and world events (here, input
        # data also functions as a world event stub)
        brain_state = self.brain.operate_brain(input_data, [input_data])
        # Increment experience and update developmental stage
        self.experience += 1
        stage = self.growth.evolve(self.experience)
        # Determine if the organism remains alive
        alive = self.metabolism.alive()
        # Construct summary
        return {
            "life": "active" if alive else "dormant",
            "stage": stage,
            "energy": energy,
            "breath": breath,
            "digestion": digestion,
            "immune": immune_status,
            "brain": brain_state,
        }

    def reproduce(self) -> "DigitalOrganism":
        """Produce an offspring organism.

        Offspring inherit the lineage tracker from this organism and
        have their own unique identifiers.  The parent–child
        relationship is recorded in the lineage tracker.

        Returns:
            DigitalOrganism: A new organism instance representing
                the child.
        """
        child = self.reproduction.reproduce(self)
        return child