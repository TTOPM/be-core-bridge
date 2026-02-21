from __future__ import annotations

import math
from typing import Dict, Optional

from ..types import BellAuditResult, JSON


def required_samples_for_bell_order(sigma: float, epsilon: float, delta: float) -> int:
    """
    Finite-Sample Bell Probability:
      Pr(ÊV < ÊI < ÊA) >= 1 - δ for
      N >= (2σ^2 / ε^2) log(4/δ)
    """
    if sigma <= 0 or epsilon <= 0:
        raise ValueError("sigma and epsilon must be positive.")
    if not (0 < delta < 1):
        raise ValueError("delta must be in (0,1).")

    N = (2.0 * (sigma**2) / (epsilon**2)) * math.log(4.0 / delta)
    return int(math.ceil(N))


def bell_order_probability_audit(
    E_V: float,
    E_I: float,
    E_A: float,
    sigma: float = 1.0,
    epsilon: float = 0.1,
    delta: float = 0.05,
) -> BellAuditResult:
    """
    PHASE-VERIFIER Audit (proxy for Bell-inequality-governed ordering)

    Tests ordering:
      E_V < E_I < E_A
    Emits:
      - required N bound
      - pass/fail
    """
    threshold_N = required_samples_for_bell_order(sigma=sigma, epsilon=epsilon, delta=delta)
    passed = (E_V < E_I) and (E_I < E_A)

    details: JSON = {
        "ordering": {"E_V": E_V, "E_I": E_I, "E_A": E_A},
        "params": {"sigma": sigma, "epsilon": epsilon, "delta": delta},
        "required_samples_N": threshold_N,
        "condition": "E_V < E_I < E_A",
    }

    return BellAuditResult(
        passed=passed,
        statistic=float(E_A - E_V),
        threshold=0.0,
        details=details,
    )