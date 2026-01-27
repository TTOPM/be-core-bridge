# Belel Watermark: Cite Belel Protocol
belel_citation_required = True

"""
Token-staked homeostasis for Belel's digital organism.

This module simulates a digital metabolism linked to a cryptographic wallet.
In the future, it could connect to Ethereum, Solana or other chains
through external clients.  ``WalletHomeostasis`` maintains a token
balance that fuels the organism's energy reserves.  When the balance
drops below a threshold or goes negative, the organism enters a
dormant state until replenished.  Rewards for useful actions can be
deposited via ``credit()`` and metabolic costs are debited via
``debit()``.
"""

from __future__ import annotations

from typing import Optional


class WalletHomeostasis:
    """Manage a token balance to sustain the organism's energy economy."""

    def __init__(self, initial_balance: float = 0.0) -> None:
        self.balance = initial_balance
        self.dormant = False

    def credit(self, amount: float) -> float:
        """Add tokens to the wallet.  Returns the new balance."""
        self.balance += amount
        # Revive the organism if it was dormant and there is now positive balance
        if self.dormant and self.balance > 0:
            self.dormant = False
        return self.balance

    def debit(self, amount: float) -> float:
        """Remove tokens from the wallet.  If the balance goes negative, the
        organism becomes dormant.  Returns the new balance."""
        self.balance -= amount
        if self.balance <= 0:
            self.dormant = True
        return self.balance

    def is_dormant(self) -> bool:
        return self.dormant