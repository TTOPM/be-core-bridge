"""
Initialization for the frontiers modules package.

This package exposes the domain-specific modules that implement guidance and
artifact generation for the quantum, bio, multiverse, and xeno frontiers.
"""

from .quantum_entanglement_guard import QuantumEntanglementGuard
from .bio_digital_interface import BioDigitalInterface
from .multiverse_adjudicator import MultiverseAdjudicator
from .xeno_covenant import XenoCovenant
from .alien_technology import AlienTechnology
from .sentience_core import SentienceCore
from .belief_affirmation import BeliefAffirmation
from ..evolutionary.rl_emergence import RLEmergence

__all__ = [
    "QuantumEntanglementGuard",
    "BioDigitalInterface",
    "MultiverseAdjudicator",
    "XenoCovenant",
    "AlienTechnology",
    "SentienceCore",
    "RLEmergence",
    "BeliefAffirmation",
]