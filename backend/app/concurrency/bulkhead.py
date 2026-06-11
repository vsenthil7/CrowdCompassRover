"""Concurrency limiting (bulkhead pattern).

Caps the number of simultaneous in-flight operations against an expensive dependency so a
spike cannot exhaust resources or overwhelm a downstream. Optionally bounds the wait queue:
when both the active slots and the queue are full, the call is rejected fast with a typed
error rather than piling up unboundedly. Complements the circuit breaker (which trips on
failures) by protecting against load.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

from app.errors.exceptions import RoverError

T = TypeVar("T")


class BulkheadFullError(RoverError):
    """Raised when both the concurrency slots and the wait queue are full."""

    status_code = 503
    code = "bulkhead_full"
    title = "Service Busy"


@dataclass
class BulkheadStats:
    """Point-in-time bulkhead utilisation."""

    name: str
    max_concurrent: int
    active: int
    queued: int
    rejected: int


class Bulkhead:
    """Limits concurrent executions, with a bounded wait queue."""

    def __init__(self, name: str, *, max_concurrent: int = 10, max_queue: int = 50) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be >= 1")
        self.name = name
        self.max_concurrent = max_concurrent
        self.max_queue = max_queue
        self._sem = asyncio.Semaphore(max_concurrent)
        self._active = 0
        self._queued = 0
        self._rejected = 0

    async def run(self, fn: Callable[[], Awaitable[T]]) -> T:
        """Execute ``fn`` within the concurrency limit, or reject if saturated."""
        if self._active >= self.max_concurrent and self._queued >= self.max_queue:
            self._rejected += 1
            raise BulkheadFullError(f"bulkhead '{self.name}' is full")
        self._queued += 1
        queued = True
        try:
            async with self._sem:
                self._queued -= 1
                queued = False
                self._active += 1
                try:
                    return await fn()
                finally:
                    self._active -= 1
        finally:
            if queued:
                self._queued -= 1

    def stats(self) -> BulkheadStats:
        return BulkheadStats(
            name=self.name,
            max_concurrent=self.max_concurrent,
            active=self._active,
            queued=self._queued,
            rejected=self._rejected,
        )
