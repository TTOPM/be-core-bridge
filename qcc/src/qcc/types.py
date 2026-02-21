from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol, Sequence


JSON = Dict[str, Any]


class LoadStateFn(Protocol):
    def __call__(self, path: str) -> JSON: ...


class PersistStateFn(Protocol):
    def __call__(self, state: JSON) -> None: ...


class SwarmMutateFn(Protocol):
    def __call__(self, state: JSON) -> JSON: ...


class ConcordiumFilterFn(Protocol):
    def __call__(self, mutated_state: JSON) -> bool: ...


class LogViolationFn(Protocol):
    def __call__(self, message: str, context: Optional[JSON] = None) -> None: ...


@dataclass(frozen=True)
class BellAuditResult:
    passed: bool
    statistic: float
    threshold: float
    details: JSON