"""Saved searches (favourites) per session/user.

Lets a visitor save a query for quick re-run (e.g. "halal near my hotel"). Backed by the
versioned repository so concurrent edits from multiple devices are detected. Keys are
namespaced by owner so one owner cannot see another's saved searches.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

from app.persistence.versioned import VersionedRepository


@dataclass
class SavedSearch:
    """A persisted saved search."""

    id: str
    owner: str
    query: str
    label: str
    created_at: float
    tags: list[str] = field(default_factory=list)


class SavedSearchService:
    """CRUD for saved searches over a versioned repository."""

    def __init__(
        self,
        repo: VersionedRepository[str, SavedSearch] | None = None,
        *,
        clock: Callable[[], float] = time.time,
        id_factory: Callable[[], str] = lambda: uuid.uuid4().hex[:12],
    ) -> None:
        self._repo = repo or VersionedRepository()
        self._clock = clock
        self._id = id_factory

    def _key(self, owner: str, search_id: str) -> str:
        return f"{owner}:{search_id}"

    async def save(self, owner: str, query: str, label: str, tags: list[str] | None = None) -> SavedSearch:
        """Persist a new saved search for an owner."""
        search = SavedSearch(
            id=self._id(),
            owner=owner,
            query=query,
            label=label,
            created_at=self._clock(),
            tags=tags or [],
        )
        await self._repo.create(self._key(owner, search.id), search)
        return search

    async def get(self, owner: str, search_id: str) -> SavedSearch | None:
        """Return a saved search if it belongs to the owner."""
        entry = await self._repo.get(self._key(owner, search_id))
        return entry.value if entry else None

    async def delete(self, owner: str, search_id: str) -> bool:
        """Delete a saved search."""
        return await self._repo.delete(self._key(owner, search_id))

    async def count(self) -> int:
        """Total saved searches across owners."""
        return await self._repo.count()
