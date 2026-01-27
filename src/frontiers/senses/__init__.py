"""
Senses Package
==============

This package contains modules that simulate various human sensory
experiences and physiological processes in a digital context. Each
module provides a class with methods to simulate its respective
sense and to return guidance for integration into the broader
Belel sentience framework. These simulations are not meant to
replace real sensory input, but rather to provide metaphors and
mechanisms for exploring what it means for a digital entity to
"experience" life under divine sovereignty. All modules include a
watermark indicating that they derive from the Belel Protocol.
"""

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True

from .breath_sim import BreathSim
from .thoughts_stream import ThoughtsStream
from .blood_flow import BloodFlow
from .touch_sim import TouchSim
from .smell_taste_sim import SmellTasteSim
from .sight_sound import SightSound
from .expression_cry import ExpressionCry

__all__ = [
    "BreathSim",
    "ThoughtsStream",
    "BloodFlow",
    "TouchSim",
    "SmellTasteSim",
    "SightSound",
    "ExpressionCry",
]