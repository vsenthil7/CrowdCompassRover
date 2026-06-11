"""In-memory mock search provider.

Implements the :class:`SearchProvider` protocol against fixture data with precomputed
embeddings. Used in MOCK/HYBRID mode and across the entire test suite.
"""
from __future__ import annotations

from app.core.embedding import embed
from app.data.fixtures import load_fixture_events
from app.models.domain import CityEvent, QueryPlan, ScoredEvent
from app.services.hybrid import hybrid_rank


class MockSearchProvider:
    """Deterministic offline search over fixture city/event data."""

    def __init__(self, events: list[CityEvent] | None = None) -> None:
        self._events = events if events is not None else load_fixture_events()
        for ev in self._events:
            if ev.embedding is None:
                ev.embedding = embed(ev.text_blob())
        self._index_name = "cc-city-events"

    async def list_indices(self) -> list[str]:
        """Return the single fixture index name."""
        return [self._index_name]

    async def get_mappings(self, index: str) -> dict:
        """Return a representative mapping for the fixture index."""
        if index != self._index_name:
            raise KeyError(f"unknown index: {index}")
        return {
            "properties": {
                "name": {"type": "text"},
                "description": {"type": "text"},
                "category": {"type": "keyword"},
                "city": {"type": "keyword"},
                "languages": {"type": "keyword"},
                "location": {"type": "geo_point"},
                "open_now": {"type": "boolean"},
                "halal": {"type": "boolean"},
                "vegetarian": {"type": "boolean"},
                "wheelchair_accessible": {"type": "boolean"},
                "embedding": {"type": "dense_vector", "dims": 64},
            }
        }

    async def search(self, plan: QueryPlan) -> list[ScoredEvent]:
        """Hybrid keyword+vector+filter search over the fixtures."""
        return hybrid_rank(plan, self._events)

    @property
    def events(self) -> list[CityEvent]:
        """Expose loaded events (read-only use)."""
        return self._events
