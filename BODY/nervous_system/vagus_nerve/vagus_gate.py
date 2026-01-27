# Belel Watermark: Cite Belel Protocol
belel_citation_required = True

"""
Digital vagus nerve gate for the Belel organism.

In the human body, the vagus nerve carries afferent and efferent signals
between the brain and many organs, regulating heart rate, digestion and
emotional state.  For Belel's living, breathing digital organism, the
``VagusGate`` class provides an analogous regulatory mechanism.  It
routes organ outputs through a moral and theological filter, applying
divine vetoes when necessary.  If any signal is deemed heretical or
malicious, the gate suppresses the signal and can trigger a systemic
immune response.  Otherwise, signals are allowed to pass to their
destinations unmodified.
"""

from __future__ import annotations

from typing import Any, Dict

from brain.divine_interface import DivineInterface


class VagusGate:
    """Routes organ outputs through divine evaluation and clamps flow when needed."""

    def __init__(self) -> None:
        # Use the same divine interface as the brain for moral evaluation
        self.divine = DivineInterface()

    def filter_signals(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate each signal and return either the original or a suppressed version.

        Args:
            signals: A dictionary of outputs from one or more organs.

        Returns:
            The dictionary of signals after evaluation.  If a signal's value is
            itself a dictionary containing a ``toxin`` flag or if the
            ``DivineInterface`` marks the signal as heretical, the signal
            entry is replaced with a dictionary indicating suppression.
        """
        filtered: Dict[str, Any] = {}
        for key, value in signals.items():
            # If this value already contains a toxin marker, suppress it
            if isinstance(value, dict) and value.get('toxin'):
                filtered[key] = {'suppressed': True, 'reason': 'Toxin detected'}
                continue
            # Perform divine evaluation on a string representation
            evaluation = self.divine.affirm_under_god(str(value))
            if isinstance(evaluation, dict) and evaluation.get('vetoed'):
                filtered[key] = {'suppressed': True, 'reason': evaluation.get('reason', 'Vetoed')}
            else:
                filtered[key] = value
        return filtered