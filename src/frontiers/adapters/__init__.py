"""
Adapters for integrating frontiers functionality with existing Belel infrastructure.

These adapters provide abstractions for logging and veto evaluation based on the
repository's existing components such as `divine_inspiration_log.py` and
`gospel_integrity_manifest.yml` without modifying them.
"""

from .divine_logger import DivineLoggerAdapter
from .gospel_veto import GospelVetoAdapter, VetoDecision

__all__ = [
    "DivineLoggerAdapter",
    "GospelVetoAdapter",
    "VetoDecision",
]