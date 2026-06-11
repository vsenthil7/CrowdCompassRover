"""Admin / operations surface.

Bundles operational actions an on-call engineer needs at runtime: flush the search cache,
trigger a reindex (re-run ingestion into the event repository), and inspect effective
configuration and feature flags. Kept as a service so it can be guarded by auth at the API
edge and unit-tested in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.flags.feature_flags import FeatureFlags
from app.ingestion.pipeline import FreshnessTracker, IngestionPipeline
from app.persistence.repository import EventRepository
from app.resilience.cache import TTLCache


@dataclass
class ReindexResult:
    """Outcome of a reindex operation."""

    indexed: int
    healthy: bool


class AdminService:
    """Runtime operational actions."""

    def __init__(
        self,
        *,
        cache: TTLCache,
        events: EventRepository,
        pipeline: IngestionPipeline,
        freshness: FreshnessTracker,
        flags: FeatureFlags,
    ) -> None:
        self._cache = cache
        self._events = events
        self._pipeline = pipeline
        self._freshness = freshness
        self._flags = flags

    async def flush_cache(self) -> dict:
        """Clear the search cache and report prior stats."""
        stats = {"hits": self._cache.hits, "misses": self._cache.misses, "size": self._cache.size}
        await self._cache.clear()
        return {"flushed": True, "previous": stats}

    async def reindex(self) -> ReindexResult:
        """Re-run ingestion and bulk-load results into the event repository."""
        report = await self._pipeline.run()
        await self._events.bulk_put(report.events)
        self._freshness.mark()
        return ReindexResult(indexed=len(report.events), healthy=report.healthy)

    def flags_snapshot(self) -> dict[str, bool]:
        """Return the current evaluated flags."""
        return self._flags.all_flags()

    async def status(self) -> dict:
        """Return an operational status summary."""
        return {
            "events": await self._events.count(),
            "cache_size": self._cache.size,
            "cache_hit_rate": round(self._cache.hit_rate, 4),
            "data_stale": self._freshness.is_stale,
            "data_age_seconds": self._freshness.age_seconds,
            "flags": self._flags.all_flags(),
        }
