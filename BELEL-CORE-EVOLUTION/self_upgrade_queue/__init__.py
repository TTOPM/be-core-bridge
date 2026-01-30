"""
Self Upgrade Queue (Belel Core Evolution)

This package is the intake buffer for upgrade requests.
It accepts proposals, validates schema, writes to disk, and emits a reference ID.

No execution happens here.
Execution is only permitted after governance_filters approval.
"""

from .queue import (
    UpgradeRequest,
    load_policy,
    validate_request,
    write_request,
    list_requests,
)

__all__ = [
    "UpgradeRequest",
    "load_policy",
    "validate_request",
    "write_request",
    "list_requests",
]
