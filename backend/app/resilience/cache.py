"""An async-safe TTL + LRU cache.

Used to memoise search results for hot queries during matchday spikes. Entries expire
after a TTL and the least-recently-used entry is evicted when capacity is exceeded. A
clock is injected so expiry is testable without sleeping.
"""
from __future__ import annotations

import asyncio
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, Hashable, TypeVar

V = TypeVar("V")


@dataclass
class _Entry(Generic[V]):
    value: V
    expires_at: float


class TTLCache(Generic[V]):
    """Bounded TTL cache with LRU eviction and hit/miss stats."""

    def __init__(
        self,
        *,
        maxsize: int = 256,
        ttl: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.maxsize = maxsize
        self.ttl = ttl
        self._clock = clock
        self._store: "OrderedDict[Hashable, _Entry[V]]" = OrderedDict()
        self._lock = asyncio.Lock()
        self.hits = 0
        self.misses = 0

    def _is_live(self, entry: _Entry[V]) -> bool:
        return entry.expires_at > self._clock()

    async def get(self, key: Hashable) -> V | None:
        """Return a live cached value or ``None``."""
        async with self._lock:
            entry = self._store.get(key)
            if entry is None or not self._is_live(entry):
                if entry is not None:
                    del self._store[key]
                self.misses += 1
                return None
            self._store.move_to_end(key)
            self.hits += 1
            return entry.value

    async def set(self, key: Hashable, value: V) -> None:
        """Store a value, evicting the LRU entry if over capacity."""
        async with self._lock:
            self._store[key] = _Entry(value, self._clock() + self.ttl)
            self._store.move_to_end(key)
            while len(self._store) > self.maxsize:
                self._store.popitem(last=False)

    async def get_or_set(self, key: Hashable, factory: Callable[[], Awaitable[V]]) -> V:
        """Return cached value or compute, store, and return it."""
        cached = await self.get(key)
        if cached is not None:
            return cached
        value = await factory()
        await self.set(key, value)
        return value

    async def clear(self) -> None:
        """Empty the cache (stats preserved)."""
        async with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        """Number of stored entries (including any not-yet-evicted expired)."""
        return len(self._store)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate in [0, 1]."""
        total = self.hits + self.misses
        return self.hits / total if total else 0.0
