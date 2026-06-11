"""Query analytics and audit trail.

Records a structured event per search/chat so product teams can see what visitors ask,
which languages appear, hit/miss rates, and zero-result queries (a gap signal). Events are
appended to a bounded in-memory buffer and also emitted to the structured log for
durable capture. Aggregation helpers power a lightweight analytics endpoint.
"""
from __future__ import annotations

import logging
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Callable, Deque

from app.observability.logging_config import get_logger, log_event

_logger = get_logger("analytics")


@dataclass
class QueryEvent:
    """A single recorded query event."""

    query: str
    language: str
    result_count: int
    category: str | None
    city: str | None
    duration_ms: float
    ts: float


@dataclass
class AnalyticsSnapshot:
    """Aggregated view over recorded events."""

    total: int
    zero_result: int
    by_language: dict[str, int] = field(default_factory=dict)
    by_category: dict[str, int] = field(default_factory=dict)
    top_queries: list[tuple[str, int]] = field(default_factory=list)

    @property
    def zero_result_rate(self) -> float:
        """Fraction of queries returning no results."""
        return self.zero_result / self.total if self.total else 0.0


class AnalyticsRecorder:
    """Collects query events and produces aggregate snapshots."""

    def __init__(self, *, maxlen: int = 10000, clock: Callable[[], float] = time.time) -> None:
        self._events: Deque[QueryEvent] = deque(maxlen=maxlen)
        self._clock = clock

    def record(
        self,
        query: str,
        language: str,
        result_count: int,
        *,
        category: str | None = None,
        city: str | None = None,
        duration_ms: float = 0.0,
    ) -> QueryEvent:
        """Record one query event and emit it to the structured log."""
        event = QueryEvent(
            query=query,
            language=language,
            result_count=result_count,
            category=category,
            city=city,
            duration_ms=duration_ms,
            ts=self._clock(),
        )
        self._events.append(event)
        log_event(
            _logger,
            logging.INFO,
            "query",
            language=language,
            result_count=result_count,
            category=category,
            city=city,
            duration_ms=duration_ms,
        )
        return event

    def snapshot(self, top_n: int = 10) -> AnalyticsSnapshot:
        """Aggregate the recorded events into a snapshot."""
        languages: Counter = Counter()
        categories: Counter = Counter()
        queries: Counter = Counter()
        zero = 0
        for ev in self._events:
            languages[ev.language] += 1
            if ev.category:
                categories[ev.category] += 1
            queries[ev.query.lower()] += 1
            if ev.result_count == 0:
                zero += 1
        return AnalyticsSnapshot(
            total=len(self._events),
            zero_result=zero,
            by_language=dict(languages),
            by_category=dict(categories),
            top_queries=queries.most_common(top_n),
        )

    @property
    def size(self) -> int:
        """Number of buffered events."""
        return len(self._events)
