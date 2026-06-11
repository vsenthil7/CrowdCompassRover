"""Idempotency support for unsafe (POST) operations.

Clients supply an ``Idempotency-Key``; the store remembers the response for that key for a
TTL so a retried request returns the original result instead of re-executing. An in-flight
marker prevents two concurrent requests with the same key from both executing. Time is
injected for deterministic tests.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class KeyState(str, Enum):
    NEW = "new"
    IN_FLIGHT = "in_flight"
    COMPLETED = "completed"


@dataclass
class _Record:
    state: KeyState
    response: Any
    expires_at: float


class IdempotencyStore:
    """Tracks idempotency keys and their cached responses."""

    def __init__(self, *, ttl: float = 86400.0, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl = ttl
        self._clock = clock
        self._records: dict[str, _Record] = {}
        self._lock = asyncio.Lock()

    def _live(self, record: _Record) -> bool:
        return record.expires_at > self._clock()

    async def begin(self, key: str) -> tuple[KeyState, Any]:
        """Mark a key in-flight if new; return (prior_state, cached_response)."""
        async with self._lock:
            record = self._records.get(key)
            if record is not None and self._live(record):
                return record.state, record.response
            self._records[key] = _Record(
                state=KeyState.IN_FLIGHT, response=None, expires_at=self._clock() + self.ttl
            )
            return KeyState.NEW, None

    async def complete(self, key: str, response: Any) -> None:
        """Store the final response for a key."""
        async with self._lock:
            self._records[key] = _Record(
                state=KeyState.COMPLETED,
                response=response,
                expires_at=self._clock() + self.ttl,
            )

    async def release(self, key: str) -> None:
        """Remove an in-flight marker (e.g. on failure) so it can be retried."""
        async with self._lock:
            record = self._records.get(key)
            if record is not None and record.state == KeyState.IN_FLIGHT:
                del self._records[key]

    @property
    def size(self) -> int:
        return len(self._records)
