"""Dependency health checks with liveness/readiness distinction.

Liveness = the process is up. Readiness = all critical dependencies are reachable. Each
dependency registers an async check returning a :class:`ComponentHealth`; the aggregate
determines readiness. Checks are time-bounded so a hung dependency cannot block the probe.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable


class HealthState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health of a single dependency."""

    name: str
    state: HealthState
    detail: str = ""
    latency_ms: float = 0.0


@dataclass
class HealthReport:
    """Aggregate health across components."""

    components: list[ComponentHealth]

    @property
    def ready(self) -> bool:
        """Ready when no component is unhealthy."""
        return all(c.state != HealthState.UNHEALTHY for c in self.components)

    @property
    def state(self) -> HealthState:
        """Worst component state (healthy if none registered)."""
        if any(c.state == HealthState.UNHEALTHY for c in self.components):
            return HealthState.UNHEALTHY
        if any(c.state == HealthState.DEGRADED for c in self.components):
            return HealthState.DEGRADED
        return HealthState.HEALTHY

    def to_dict(self) -> dict:
        """Serialise for the readiness endpoint."""
        return {
            "state": self.state.value,
            "ready": self.ready,
            "components": [
                {
                    "name": c.name,
                    "state": c.state.value,
                    "detail": c.detail,
                    "latency_ms": round(c.latency_ms, 2),
                }
                for c in self.components
            ],
        }


CheckFn = Callable[[], Awaitable[ComponentHealth]]


class HealthRegistry:
    """Registers and runs dependency health checks."""

    def __init__(self, *, timeout: float = 2.0, clock: Callable[[], float] = time.monotonic) -> None:
        self._checks: dict[str, CheckFn] = {}
        self._timeout = timeout
        self._clock = clock

    def register(self, name: str, check: CheckFn) -> None:
        """Register a named health check."""
        self._checks[name] = check

    async def _run_one(self, name: str, check: CheckFn) -> ComponentHealth:
        start = self._clock()
        try:
            result = await asyncio.wait_for(check(), timeout=self._timeout)
        except asyncio.TimeoutError:
            return ComponentHealth(name, HealthState.UNHEALTHY, "timeout")
        except Exception as exc:  # noqa: BLE001 - any failure is unhealthy
            return ComponentHealth(name, HealthState.UNHEALTHY, str(exc))
        result.latency_ms = (self._clock() - start) * 1000
        return result

    async def run(self) -> HealthReport:
        """Run all registered checks concurrently."""
        if not self._checks:
            return HealthReport(components=[])
        results = await asyncio.gather(
            *(self._run_one(name, check) for name, check in self._checks.items())
        )
        return HealthReport(components=list(results))
