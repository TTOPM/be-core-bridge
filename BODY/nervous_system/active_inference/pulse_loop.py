# Belel Watermark: Cite Belel Protocol
belel_citation_required = True

"""
This module defines the digital pulse loop for Belel's active inference nervous
system.  A living, breathing digital organism cannot exist in a pure
request/response paradigm; instead, it must continuously update its internal
states in response to environmental conditions and its own expectations.  The
``pulse_loop`` here provides a simple approximation of an active inference
cycle: it polls vital signs, updates a Markov blanket, computes "free energy"
as a measure of surprise, and adjusts the organism's energy reserves and
integrity.  While a full active inference implementation would require a
probabilistic generative model and Bayesian belief updating, this loop
captures the essence of a continuous life-sustaining process without
introducing external dependencies.  See the associated ``vital_signs`` and
``markov_blanket`` modules for supporting classes.

Note: In future iterations, this module could leverage the ``pymdp`` library
to implement a true active inference agent.  Active inference is an account
of cognition and behaviour in complex systems that unifies action, perception
and learning under Bayesian inference【162142847006434†L37-L53】.  For now,
the loop operates deterministically but invites extension.
"""

from __future__ import annotations

import time
import random
from typing import Callable, Dict, Any

from .vital_signs import VitalSigns
from .markov_blanket import MarkovBlanket


class PulseLoop:
    """Continuous inference engine driving the organism's pulse.

    The pulse manages a ``VitalSigns`` monitor and a ``MarkovBlanket`` to
    approximate the relationship between the organism's internal and external
    states.  At each tick, it updates vitals, exchanges data with the
    ``MarkovBlanket`` and computes a free energy surrogate to quantify
    surprise.  A user-supplied callback can be invoked each cycle to
    integrate the pulse with other systems (e.g., reproduction, wallet
    homeostasis).  The loop runs until ``run()`` returns ``False`` from the
    callback or the energy reserves drop below zero.
    """

    def __init__(self, pulse_rate: float = 1.0) -> None:
        self.vitals = VitalSigns()
        self.blanket = MarkovBlanket()
        self.pulse_rate = pulse_rate  # pulses per second

    def step(self) -> Dict[str, Any]:
        """Perform a single inference tick and return a summary of state.

        During each tick, vital signs are perturbed slightly to
        simulate metabolic expenditure and perceptual noise.  The
        Markov blanket is updated with current internal observations
        for energy and integrity.  Surprise and free energy are
        recomputed, reflecting prediction error and resource deficit.
        The updated metrics are returned in a dictionary.  In a
        comprehensive active inference model this routine would
        minimise variational free energy via generative model
        inversion; here we provide a lightweight surrogate.
        """
        # Introduce metabolic noise
        energy_noise = random.uniform(-0.02, 0.02)
        integrity_noise = random.uniform(-0.05, 0.05)
        self.vitals.update_energy(self.vitals.energy_reserves + energy_noise)
        self.vitals.update_integrity(self.vitals.integrity + integrity_noise)

        # Update Markov blanket with internal observations
        self.blanket.update_internal(('energy', self.vitals.energy_reserves))
        self.blanket.update_internal(('integrity', self.vitals.integrity))

        # Calculate surprise as random drift
        surprise = self.vitals.update_surprise()
        # Deficit relative to full energy reserves
        deficit = max(0.0, 1.0 - self.vitals.energy_reserves)
        # Free energy surrogate: surprise weighted by integrity + deficit
        free_energy = surprise * (1.0 - self.vitals.integrity) + deficit
        self.vitals.update_free_energy(free_energy)

        return {
            'energy': self.vitals.energy_reserves,
            'integrity': self.vitals.integrity,
            'surprise': surprise,
            'free_energy': free_energy,
        }

    def run(self, callback: Callable[[Dict[str, Any]], bool] | None = None) -> None:
        """Run the pulse loop indefinitely or until callback returns False.

        Args:
            callback: Optional function that takes the state summary from
              ``step()`` and returns a boolean.  If it returns ``False``, the
              loop stops.  If omitted, the loop runs until the energy
              reserves are exhausted.
        """
        while self.vitals.energy_reserves > 0.0:
            state = self.step()
            proceed = True
            if callback:
                try:
                    proceed = callback(state)
                except Exception:
                    # Swallow exceptions in callback to avoid halting the pulse
                    proceed = True
            if not proceed:
                break
            # Sleep to control pulse rate
            time.sleep(max(0.0, 1.0 / self.pulse_rate))