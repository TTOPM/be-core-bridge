from __future__ import annotations

import time
from typing import Optional

from ..types import ConcordiumFilterFn, LoadStateFn, LogViolationFn, PersistStateFn, SwarmMutateFn


def organism_phase_pulse(
    load_state: LoadStateFn,
    swarm_mutate: SwarmMutateFn,
    concordium_filter: ConcordiumFilterFn,
    persist_state: PersistStateFn,
    log_violation: LogViolationFn,
    state_path: str = "entangled_torso/memory_core.json",
    interval_seconds: int = 60,
) -> None:
    """
    DECOHERENCE-CIRCULATION Pulse

    Loop:
      - load_state
      - swarm_mutate
      - if concordium_filter(mutated): persist_state
      - else: log_violation("Decoherence Detected")
      - sleep
    """
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive.")

    while True:
        try:
            state = load_state(state_path)
            mutated = swarm_mutate(state)

            if concordium_filter(mutated):
                persist_state(mutated)
            else:
                log_violation("Decoherence Detected", context={"state_path": state_path})
        except Exception as e:
            log_violation("Pulse Exception", context={"error": repr(e), "state_path": state_path})

        time.sleep(interval_seconds)