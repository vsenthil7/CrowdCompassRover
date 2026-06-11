"""Repository abstractions (persistence ports).

Defines storage interfaces independent of any backend. The in-memory implementations are
used offline and in tests; a real deployment would add Firestore/Postgres adapters that
satisfy the same protocols, so call sites never change. This is the hexagonal
"ports and adapters" boundary for persistence.
"""
from __future__ import annotations

from typing import Generic, Protocol, TypeVar, runtime_checkable

from app.models.domain import CityEvent

T = TypeVar("T")
K = TypeVar("K")


@runtime_checkable
class Repository(Protocol, Generic[K, T]):
    """Generic async CRUD repository."""

    async def get(self, key: K) -> T | None:
        """Return an entity by key or None."""
        ...

    async def put(self, key: K, value: T) -> None:
        """Insert or replace an entity."""
        ...

    async def delete(self, key: K) -> bool:
        """Delete an entity; return whether it existed."""
        ...

    async def list_all(self) -> list[T]:
        """Return all entities."""
        ...

    async def count(self) -> int:
        """Return the number of stored entities."""
        ...


@runtime_checkable
class EventRepository(Protocol):
    """Repository specialised for city/event documents with bulk + query helpers."""

    async def get(self, key: str) -> CityEvent | None:
        """Return an event by id."""
        ...

    async def put(self, key: str, value: CityEvent) -> None:
        """Insert or replace an event."""
        ...

    async def bulk_put(self, events: list[CityEvent]) -> int:
        """Insert or replace many events; return the count written."""
        ...

    async def list_all(self) -> list[CityEvent]:
        """Return all events."""
        ...

    async def by_city(self, city: str) -> list[CityEvent]:
        """Return events filtered by city (case-insensitive)."""
        ...

    async def count(self) -> int:
        """Return number of stored events."""
        ...
