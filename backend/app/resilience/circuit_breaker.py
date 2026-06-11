"""A three-state circuit breaker (closed → open → half-open).

Protects upstreams from cascading failure: after ``fail_max`` consecutive failures the
breaker opens and fast-fails calls for ``reset_timeout`` seconds, then allows a single
trial (half-open). A success closes it; a failure re-opens it. Time is injected for
deterministic tests.
"""
from __future__ import annotations

import time
from enum import Enum
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when a call is rejected because the breaker is open."""


class CircuitBreaker:
    """Consecutive-failure circuit breaker for async callables."""

    def __init__(
        self,
        name: str,
        *,
        fail_max: int = 5,
        reset_timeout: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._opened_at = 0.0

    @property
    def state(self) -> CircuitState:
        """Current state, accounting for elapsed reset timeout."""
        if self._state == CircuitState.OPEN:
            if self._clock() - self._opened_at >= self.reset_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def _on_success(self) -> None:
        self._failures = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.fail_max or self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._opened_at = self._clock()

    async def call(self, op: Callable[[], Awaitable[T]]) -> T:
        """Execute ``op`` subject to the breaker state."""
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError(f"circuit '{self.name}' is open")
        try:
            result = await op()
        except Exception:
            self._on_failure()
            raise
        else:
            self._on_success()
            return result
