"""The ingestion pipeline: pull sources, normalise, track freshness.

Coordinates multiple feed sources, aggregates normalised events, deduplicates by id
(last-write-wins), and records per-source freshness so the API can surface staleness. This
is the offline-capable backbone that, in real mode, would bulk-index into Elasticsearch
via the MCP client.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable

from app.ingestion.normalizer import normalise_source
from app.ingestion.sources import FeedSource
from app.models.domain import CityEvent
from app.observability.logging_config import get_logger, log_event

_logger = get_logger("ingestion")


@dataclass
class SourceStatus:
    """Freshness and health for a single source."""

    name: str
    last_run: float
    accepted: int
    rejected: int
    ok: bool
    error: str | None = None


@dataclass
class IngestionReport:
    """Aggregate outcome of a pipeline run."""

    events: list[CityEvent] = field(default_factory=list)
    statuses: list[SourceStatus] = field(default_factory=list)

    @property
    def total_accepted(self) -> int:
        return sum(s.accepted for s in self.statuses)

    @property
    def total_rejected(self) -> int:
        return sum(s.rejected for s in self.statuses)

    @property
    def healthy(self) -> bool:
        return all(s.ok for s in self.statuses)


class IngestionPipeline:
    """Runs a set of feed sources and produces a deduplicated event set."""

    def __init__(
        self,
        sources: list[FeedSource],
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._sources = sources
        self._clock = clock

    async def run(self) -> IngestionReport:
        """Fetch and normalise every source, aggregating results."""
        report = IngestionReport()
        by_id: dict[str, CityEvent] = {}
        for source in self._sources:
            try:
                result = await normalise_source(source)
            except Exception as exc:  # noqa: BLE001 - isolate per-source failures
                report.statuses.append(
                    SourceStatus(
                        name=source.name,
                        last_run=self._clock(),
                        accepted=0,
                        rejected=0,
                        ok=False,
                        error=str(exc),
                    )
                )
                log_event(_logger, logging.ERROR, "source_failed", source=source.name)
                continue
            for event in result.events:
                by_id[event.id] = event
            report.statuses.append(
                SourceStatus(
                    name=source.name,
                    last_run=self._clock(),
                    accepted=result.accepted,
                    rejected=result.rejected,
                    ok=True,
                )
            )
            log_event(
                _logger,
                logging.INFO,
                "source_ingested",
                source=source.name,
                accepted=result.accepted,
                rejected=result.rejected,
            )
        report.events = list(by_id.values())
        return report


class FreshnessTracker:
    """Tracks the age of ingested data and classifies staleness."""

    def __init__(
        self,
        *,
        stale_after: float = 300.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.stale_after = stale_after
        self._clock = clock
        self._last_ingest: float | None = None

    def mark(self) -> None:
        """Record that a fresh ingest just completed."""
        self._last_ingest = self._clock()

    @property
    def age_seconds(self) -> float | None:
        """Seconds since the last ingest, or None if never run."""
        if self._last_ingest is None:
            return None
        return self._clock() - self._last_ingest

    @property
    def is_stale(self) -> bool:
        """Whether data is older than the staleness threshold."""
        age = self.age_seconds
        return age is None or age > self.stale_after
