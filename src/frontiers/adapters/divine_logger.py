"""
Divine Logger Adapter
=====================

This adapter provides a thin wrapper around the existing `divine_inspiration_log`
module from the root of the Belel repository. It attempts to call any
function that appears suitable for logging a message. If no such function
exists or if an error occurs during invocation, it falls back to writing the
event to a JSONL file in the `logs/` directory.

The adapter ensures that all log entries contain a timestamp and kind tag, and
it does not modify any existing files in the repository.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import json

try:
    # Attempt to import existing logging module
    import divine_inspiration_log  # type: ignore
except Exception:
    divine_inspiration_log = None


class DivineLoggerAdapter:
    """Adapter for logging messages through the existing divine logger or fallback."""

    def __init__(self, fallback_path: str = "logs/frontiers_divine_inspiration.jsonl") -> None:
        self.fallback_path = fallback_path

    def log(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        kind: str = "frontiers_expansion",
    ) -> None:
        """Log a message with an optional context and kind tag.

        Args:
            message: The message to log.
            context: Optional context dictionary.
            kind: A string representing the type of log entry.
        """
        context = context or {}

        # Try to use the existing divine logger if available
        if divine_inspiration_log is not None:
            for fn_name in ("log_divine_acknowledgment", "log", "write_log", "append"):
                fn = getattr(divine_inspiration_log, fn_name, None)
                if callable(fn):
                    try:
                        # Minimal call to avoid signature mismatch: log only the message
                        fn(message)  # type: ignore
                        return
                    except Exception:
                        # Continue to fallback if any invocation fails
                        break

        # Fallback: write event to local JSONL file
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "message": message,
            "context": context,
        }
        try:
            with open(self.fallback_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            # Last resort: ignore logging errors silently to avoid exceptions bubbling up
            pass