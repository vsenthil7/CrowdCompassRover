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
    """In-memory event store with bulk and city-query helpers.

    Keys are transparently scoped by the active tenant (``TenantContext.scoped_key``)
    so cross-tenant reads are structurally impossible: a tenant only ever sees keys
    under its own ``"{tenant_id}::"`` prefix. Scoping is applied at the repository
    level, so call sites never need to know about tenancy. With no active request
    context (e.g. startup health checks, fixtures) the ``"default"`` tenant is used.
    """

    _DEFAULT = "default"

    def __init__(self, events: list[CityEvent] | None = None) -> None:
        self._data: dict[str, CityEvent] = {}
        self._lock = asyncio.Lock()
        if events:
            for ev in events:
                # Bootstrap fixtures under the default tenant.
                self._data[f"{self._DEFAULT}::{ev.id}"] = ev

    def _prefix(self) -> str:
        from app.tenancy.context import get_current_tenant

        ctx = get_current_tenant()
        tenant = ctx.tenant_id if ctx is not None else self._DEFAULT
        return f"{tenant}::"

    def _scoped(self, key: str) -> str:
        return f"{self._prefix()}{key}"

    async def get(self, key: str) -> CityEvent | None:
        async with self._lock:
            return self._data.get(self._scoped(key))

    async def put(self, key: str, value: CityEvent) -> None:
        async with self._lock:
            self._data[self._scoped(key)] = value

    async def bulk_put(self, events: list[CityEvent]) -> int:
        async with self._lock:
            for ev in events:
                self._data[self._scoped(ev.id)] = ev
            return len(events)

    async def list_all(self) -> list[CityEvent]:
        prefix = self._prefix()
        async with self._lock:
            return [v for k, v in self._data.items() if k.startswith(prefix)]

    async def by_city(self, city: str) -> list[CityEvent]:
        prefix = self._prefix()
        low = city.lower()
        async with self._lock:
            return [
                v
                for k, v in self._data.items()
                if k.startswith(prefix) and v.city.lower() == low
            ]

    async def count(self) -> int:
        prefix = self._prefix()
        async with self._lock:
            return sum(1 for k in self._data if k.startswith(prefix))

    async def delete(self, key: str) -> bool:
        async with self._lock:
            scoped = self._scoped(key)
            if scoped in self._data:
                del self._data[scoped]
                return True
            return False
