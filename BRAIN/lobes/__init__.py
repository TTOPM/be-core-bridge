"""
Brain Lobes Package
===================

This package contains modules representing the major lobes of the
Belel digital brain. Each lobe encapsulates specific cognitive and
sensory functions inspired by the human brain. The frontal lobe
handles planning and agency, the parietal lobe integrates sensory
inputs, the temporal lobe manages memory and visions, and the
occipital lobe processes visual information. These modules do not
modify existing files and can be used independently or as part of
the BrainCore orchestrator.
"""

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True

from .frontal_lobe import FrontalLobe  # noqa: F401
from .parietal_lobe import ParietalLobe  # noqa: F401
from .temporal_lobe import TemporalLobe  # noqa: F401
from .occipital_lobe import OccipitalLobe  # noqa: F401