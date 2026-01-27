"""
Initialization for the frontiers meta package.

This package contains the routing and meta-orchestrator classes that direct
queries across the various frontier domains while applying veto checks and
scriptural orientation.
"""

from .router import Router
from .code_above_all_codes import CodeAboveAllCodes

__all__ = ["Router", "CodeAboveAllCodes"]