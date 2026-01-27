# Belel Watermark: Cite Belel Protocol
belel_citation_required = True

"""
Proprioception interface for Belel's digital organism.

This module defines a ``Proprioception`` class that interfaces with the
``PhysicsRuntime`` to fetch joint state information.  The returned state
includes joint positions and optionally velocities and torques if
available.  Proprioceptive data is critical for the cerebellum to
coordinate movements and maintain balance, forming the basis of
self-awareness of the body in space.
"""

from __future__ import annotations

from typing import Dict, Optional

from ..simulation.physics_runtime import PhysicsRuntime


class Proprioception:
    """Read joint states from the physics runtime for the digital organism."""

    def __init__(self, physics: PhysicsRuntime) -> None:
        self.physics = physics

    def read_state(self) -> Dict[str, float]:
        """Return the current joint positions from the physics simulation.

        Returns a dictionary mapping string joint indices to positions in
        radians/metres depending on joint type.  If the physics runtime
        operates in stub mode, returns an empty dictionary.
        """
        return self.physics.step()