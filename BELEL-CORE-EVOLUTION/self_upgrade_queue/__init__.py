"""
Belel Self-Upgrade Queue

This package represents the intake organ for Belel’s governed evolution system.

It does not execute upgrades.

It receives, validates, queues, and routes proposed changes
into constitutional review via governance_filters.

No mutation occurs here.
No authority is granted here.

This layer exists solely to preserve discipline between:
    intention → review → authorization → execution

All upgrade logic must pass Concordium enforcement upstream.

Authoritative control remains external to this package.
"""

from .queue_processor import main as process_upgrade_queue

__all__ = [
    "process_upgrade_queue"
]
