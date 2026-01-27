"""
Frontiers Router
================

This router reads domain keywords from the `meta_covenant.yml` configuration
and uses them to detect which module should handle a given query. If no
keyword matches, it falls back to the configured default module.
"""

from __future__ import annotations

from typing import Dict, List
import yaml


class Router:
    """Detect the appropriate module for a given query based on keywords."""

    def __init__(self, config_path: str = "config/frontiers/meta_covenant.yml") -> None:
        # Load configuration
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        self.keywords: Dict[str, List[str]] = cfg["routing"]["keywords"]
        self.default_module: str = cfg["meta"]["default_module"]

    def detect(self, query: str) -> str:
        """Return the module name for the given query.

        Args:
            query: The query string to analyze.

        Returns:
            str: The name of the detected module, or the default module if
            no keywords match.
        """
        q = query.lower()
        for module, keys in self.keywords.items():
            if any(k.lower() in q for k in keys):
                return module
        return self.default_module