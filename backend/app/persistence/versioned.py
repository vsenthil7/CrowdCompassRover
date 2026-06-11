"""Versioned in-memory repository with optimistic concurrency control.

Each stored entity carries a monotonically increasing version. Writes may supply the
expected version; a mismatch raises :class:`ConcurrencyError` instead of silently
clobbering a concurrent update. This is the in-memory analogue of an ``If-Match`` /
row-version check against a real database.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
K = TypeVar("K")


class ConcurrencyError(RuntimeError):
    """Raised when an optimistic-concurrency version check fails."""


@dataclass
class Versioned(Generic[T]):
    """An entity wrapper carrying its version."""

    value: T
    version: int


class VersionedRepository(Generic[K, T]):
    """In-memory repository with per-key versioning."""

    def __init__(self) -> None:
        self._data: dict[K, Versioned[T]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: K) -> Versioned[T] | None:
        async with self._lock:
            return self._data.get(key)

    async def create(self, key: K, value: T) -> Versioned[T]:
        """Create a new entity at version 1; fails if it already exists."""
        async with self._lock:
            if key in self._data:
                raise ConcurrencyError(f"entity already exists: {key}")
            entry = Versioned(value=value, version=1)
            self._data[key] = entry
            return entry

    async def update(self, key: K, value: T, expected_version: int) -> Versioned[T]:
        """Update an entity, enforcing the expected version."""
        async with self._lock:
            current = self._data.get(key)
            if current is None:
                raise ConcurrencyError(f"entity not found: {key}")
            if current.version != expected_version:
                raise ConcurrencyError(
                    f"version mismatch for {key}: expected {expected_version}, "
                    f"actual {current.version}"
                )
            updated = Versioned(value=value, version=current.version + 1)
            self._data[key] = updated
            return updated

    async def upsert(self, key: K, value: T) -> Versioned[T]:
        """Insert or bump version without a concurrency check."""
        async with self._lock:
            current = self._data.get(key)
            version = (current.version + 1) if current else 1
            entry = Versioned(value=value, version=version)
            self._data[key] = entry
            return entry

    async def delete(self, key: K) -> bool:
        async with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    async def count(self) -> int:
        async with self._lock:
            return len(self._data)
