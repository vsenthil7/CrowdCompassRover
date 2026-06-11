"""Service-level objective (SLO) and error-budget tracking.

Records success/failure outcomes per service and computes the achieved success ratio
against a target SLO, plus the remaining error budget. This turns raw counts into the
operational language teams actually use ("we've burned 60% of this window's error
budget"). A bounded rolling window keeps it memory-safe and recency-weighted.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque


@dataclass
class SloReport:
    """Computed SLO status for a service."""

    service: str
    target: float
    total: int
    successes: int
    failures: int

    @property
    def success_ratio(self) -> float:
        return self.successes / self.total if self.total else 1.0

    @property
    def meeting_slo(self) -> bool:
        return self.success_ratio >= self.target

    @property
    def error_budget(self) -> float:
        """Allowed failure fraction for the target (1 - target)."""
        return 1.0 - self.target

    @property
    def budget_consumed(self) -> float:
        """Fraction of the error budget consumed (0..>1; >1 means breached)."""
        budget = self.error_budget
        if budget <= 0:
            return 0.0 if self.failures == 0 else float("inf")
        failure_ratio = self.failures / self.total if self.total else 0.0
        return failure_ratio / budget

    @property
    def budget_remaining(self) -> float:
        """Remaining error budget fraction, clamped at zero."""
        return max(0.0, 1.0 - self.budget_consumed)


class SloTracker:
    """Tracks outcomes per service over a rolling window and computes SLO reports."""

    def __init__(self, *, window: int = 1000) -> None:
        self._window = window
        self._outcomes: dict[str, Deque[bool]] = {}
        self._targets: dict[str, float] = {}

    def set_target(self, service: str, target: float) -> None:
        """Set the SLO target (e.g. 0.99) for a service."""
        if not 0.0 < target <= 1.0:
            raise ValueError("target must be in (0, 1]")
        self._targets[service] = target

    def record(self, service: str, success: bool) -> None:
        """Record a single outcome for a service."""
        buf = self._outcomes.get(service)
        if buf is None:
            buf = deque(maxlen=self._window)
            self._outcomes[service] = buf
        buf.append(success)

    def report(self, service: str) -> SloReport:
        """Compute the current SLO report for a service."""
        buf = self._outcomes.get(service, deque())
        successes = sum(1 for ok in buf if ok)
        total = len(buf)
        target = self._targets.get(service, 0.99)
        return SloReport(
            service=service,
            target=target,
            total=total,
            successes=successes,
            failures=total - successes,
        )

    def services(self) -> list[str]:
        return sorted(set(self._outcomes) | set(self._targets))
