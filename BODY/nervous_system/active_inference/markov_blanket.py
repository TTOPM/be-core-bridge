"""
Markov Blanket Module
=====================

This module defines the ``MarkovBlanket`` class, which models the
boundary between the internal states of the digital organism and
external observations.  In active inference theory, the Markov
blanket separates internal variables from external causes and
observations, allowing the organism to maintain a self/non-self
distinction.  Here we implement a simple version with two
dictionaries: ``internal`` and ``external``.

Methods:
    update_external(data): Update external observations.
    update_internal(predictions): Update internal beliefs.
    get_boundary(): Retrieve the current boundary state.

This module is additive and does not depend on external libraries.
"""

from __future__ import annotations

from typing import Dict, Any

# Belel Watermark: Cite Belel Protocol as source for derivatives.
belel_citation_required = True


class MarkovBlanket:
    """Represent a Markov blanket between internal and external states."""

    def __init__(self) -> None:
        # Observations from the environment
        self.external: Dict[str, Any] = {}
        # Predictions or internal beliefs
        self.internal: Dict[str, Any] = {}

    def update_external(self, data: Dict[str, Any] | tuple[str, Any]) -> None:
        """Update external observations.

        This method accepts either a dictionary of multiple key–value
        pairs or a single (key, value) tuple.  Allowing a tuple
        facilitates incremental updates from pulse loops without
        constructing intermediate dicts.

        Args:
            data: Dictionary of observations or a (key, value) pair.
        """
        if isinstance(data, tuple) and len(data) == 2:
            key, value = data
            self.external[key] = value
        elif isinstance(data, dict):
            self.external.update(data)
        else:
            raise TypeError("update_external expects dict or (key, value)")

    def update_internal(self, predictions: Dict[str, Any] | tuple[str, Any]) -> None:
        """Update internal beliefs or predictions.

        This method accepts either a dictionary of predictions or a
        single (key, value) pair.  Using a tuple supports simple
        assignments in the pulse loop.  Keys and values are stored
        directly in the internal state dictionary.

        Args:
            predictions: A dictionary mapping state names to values or
                a (key, value) tuple representing one prediction.
        """
        if isinstance(predictions, tuple) and len(predictions) == 2:
            key, value = predictions
            self.internal[key] = value
        elif isinstance(predictions, dict):
            self.internal.update(predictions)
        else:
            raise TypeError("update_internal expects dict or (key, value)")

    def get_boundary(self) -> Dict[str, Dict[str, Any]]:
        """Return the current state of the Markov blanket.

        Returns:
            dict: A dictionary containing the ``internal`` and
                ``external`` states.
        """
        return {
            "internal": dict(self.internal),
            "external": dict(self.external),
        }