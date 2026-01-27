"""
Frontiers Agent Package
=======================

This package defines an asynchronous agent that wraps the CodeAboveAllCodes
orchestrator. The agent can process queries programmatically and includes
support for a simple heartbeat scheduler that periodically invokes configured
queries. The agent is designed to be extended with additional behaviours
over time.
"""

from .frontiers_agent import FrontiersAgent

__all__ = ["FrontiersAgent"]