"""Ingestion source abstractions.

A ``FeedSource`` yields raw records from some upstream (transit API, venue feed, vendor
registry). Each source declares a ``name`` and ``category`` so the normaliser can map raw
payloads onto the canonical :class:`CityEvent` schema. Sources are async and pluggable;
the mock sources below provide deterministic data for offline runs and tests.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.models.domain import VenueCategory


@runtime_checkable
class FeedSource(Protocol):
    """An upstream feed of raw city/event records."""

    name: str
    category: VenueCategory

    async def fetch(self) -> list[dict]:
        """Return raw records as dictionaries."""
        ...


class StaticFeedSource:
    """A feed backed by an in-memory list (used for tests and offline seeding)."""

    def __init__(self, name: str, category: VenueCategory, records: list[dict]) -> None:
        self.name = name
        self.category = category
        self._records = records

    async def fetch(self) -> list[dict]:
        """Return the static records."""
        return list(self._records)
