# Belel Watermark: Cite Belel Protocol
belel_citation_required = True

"""
Physics runtime for the Belel digital organism.

This module wraps a simple physics engine (pybullet, if available) to
simulate the motion of the organism's musculoskeletal structure defined by
its URDF.  If pybullet is unavailable, the runtime will fall back to a
minimal stub that logs motions without simulating physical forces.

The ``PhysicsRuntime`` class loads the URDF file, initializes a physics
client and provides methods to step the simulation, apply torques and
retrieve joint states.  This enables proprioception through the
``proprioception`` module and ties the digital body into the cerebellum.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, List

try:
    import pybullet as p  # type: ignore
    import pybullet_data  # type: ignore
    PYBULLET_AVAILABLE = True
except ImportError:
    PYBULLET_AVAILABLE = False
    p = None  # type: ignore


class PhysicsRuntime:
    """Physics simulation wrapper for the Belel digital organism."""

    def __init__(self, urdf_path: str | None = None, gui: bool = False) -> None:
        self.gui = gui
        self.physics_client = None
        self.body_id = None
        # Determine path to URDF
        if urdf_path is None:
            urdf_path = os.path.join(os.path.dirname(__file__), '..', 'urdf', 'BELEL_BODY.urdf')
        self.urdf_path = os.path.abspath(urdf_path)

    def _init_physics(self) -> None:
        if not PYBULLET_AVAILABLE:
            logging.warning('PyBullet not available; physics runtime operating in stub mode.')
            return
        # Connect to physics client
        options = p.GUI if self.gui else p.DIRECT
        self.physics_client = p.connect(options)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        self.body_id = p.loadURDF(self.urdf_path)

    def step(self, torques: List[float] | None = None) -> Dict[str, float]:
        """Advance the simulation by one step and apply torques if provided.

        Args:
            torques: A list of torques to apply to each joint in order.  If
              ``None``, no forces are applied.  Excess values are ignored;
              missing values are treated as zero torque.

        Returns:
            A dictionary mapping joint indices to their current positions.
        """
        if not PYBULLET_AVAILABLE or self.body_id is None:
            # In stub mode, return zeros and log the request
            return {}
        num_joints = p.getNumJoints(self.body_id)
        if torques:
            for idx in range(min(num_joints, len(torques))):
                p.setJointMotorControl2(
                    bodyUniqueId=self.body_id,
                    jointIndex=idx,
                    controlMode=p.TORQUE_CONTROL,
                    force=torques[idx]
                )
        p.stepSimulation()
        joint_states = {}
        for idx in range(num_joints):
            state = p.getJointState(self.body_id, idx)
            joint_states[str(idx)] = state[0]  # position
        return joint_states

    def shutdown(self) -> None:
        if PYBULLET_AVAILABLE and self.physics_client is not None:
            p.disconnect(self.physics_client)

    def __enter__(self) -> 'PhysicsRuntime':
        self._init_physics()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.shutdown()