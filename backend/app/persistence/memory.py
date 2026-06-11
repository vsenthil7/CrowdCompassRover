"""In-memory repository adapters.

Async-safe, dependency-free implementations of the persistence ports. They back the
offline/mock runtime and the test suite. Real adapters (Firestore, Postgres) would live
alongside these and be selected by the provider factory.
"""
from __future__ import annotations

import asyncio
from typing import Generic, TypeVar

from app.models.domain import CityEvent

T = TypeVar("T")
K = TypeVar("K")


class InMemoryRepository(Generic[K, T]):
    """A generic async-safe in-memory repository."""

    def __init__(self) -> None:
        self._data: dict[K, T] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: K) -> T | None:
        async with self._lock:
            return self._data.get(key)

    async def put(self, key: K, value: T) -> None:
        async with self._lock:
            self._data[key] = value

    async def delete(self, key: K) -> bool:
        async with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    async def list_all(self) -> list[T]:
        async with self._lock:
            return list(self._data.values())

    async def count(self) -> int:
        async with self._lock:
            return len(self._data)


class InMemoryEventRepository:
    """In-memory event store with bulk and city-query helpers."""

    def __init__(self, events: list[CityEvent] | None = None) -> None:
        self._data: dict[str, CityEvent] = {}
        self._lock = asyncio.Lock()
        if events:
            for ev in events:
                self._data[ev.id] = ev

    async def get(self, key: str) -> CityEvent | None:
        async with self._lock:
            return self._data.get(key)

    async def put(self, key: str, value: CityEvent) -> None:
        async with self._lock:
            self._data[key] = value

    async def bulk_put(self, events: list[CityEvent]) -> int:
        async with self._lock:
            for ev in events:
                self._data[ev.id] = ev
            return len(events)

    async def list_all(self) -> list[CityEvent]:
        async with self._lock:
            return list(self._data.values())

    async def by_city(self, city: str) -> list[CityEvent]:
        async with self._lock:
            low = city.lower()
            return [e for e in self._data.values() if e.city.lower() == low]

    async def count(self) -> int:
        async with self._lock:
            return len(self._data)
