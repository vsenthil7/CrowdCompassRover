"""Data retention sweeper.

Buffers are bounded by size already; retention adds a *policy* dimension: drop records
older than a configured age regardless of buffer pressure (e.g. "audit kept 365 days,
analytics 90 days"). A sweepable source exposes its records' timestamps and a way to drop
old ones; the sweeper applies each registered policy and reports how much it removed. Time
is injected for deterministic tests.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable


@runtime_checkable
class Sweepable(Protocol):
    """A source whose old records can be pruned by timestamp."""

    def prune_before(self, cutoff_ts: float) -> int:
        """Drop records with ts < cutoff; return how many were removed."""
        ...


@dataclass
class RetentionPolicy:
    """How long to keep a named source's data."""

    name: str
    max_age_seconds: float


@dataclass
class SweepResult:
    """Outcome of sweeping one source."""

    name: str
    removed: int


class RetentionSweeper:
    """Applies retention policies across registered sources."""

    def __init__(self, *, clock: Callable[[], float] = time.time) -> None:
        self._policies: list[tuple[RetentionPolicy, Sweepable]] = []
        self._clock = clock

    def register(self, policy: RetentionPolicy, source: Sweepable) -> None:
        self._policies.append((policy, source))

    def sweep(self) -> list[SweepResult]:
        """Apply every policy; return per-source removal counts."""
        now = self._clock()
        results: list[SweepResult] = []
        for policy, source in self._policies:
            cutoff = now - policy.max_age_seconds
            removed = source.prune_before(cutoff)
            results.append(SweepResult(name=policy.name, removed=removed))
        return results

    @property
    def policy_count(self) -> int:
        return len(self._policies)
