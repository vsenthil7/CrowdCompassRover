"""Intent aggregator — clusters recorded queries by their planner-assigned category.

The analytics recorder logs each query with the category the planner resolved (the closest
proxy the system has for "intent"). This aggregates those events into per-intent summaries
(count, example queries, zero-result count, average latency) for an operator dashboard.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class IntentSummary:
    """Aggregated statistics for a single query intent (category)."""

    intent: str
    count: int
    example_queries: list[str] = field(default_factory=list)
    zero_result_count: int = 0
    avg_duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "count": self.count,
            "example_queries": self.example_queries,
            "zero_result_count": self.zero_result_count,
            "avg_duration_ms": round(self.avg_duration_ms, 3),
        }


class IntentAggregator:
    """Aggregates analytics events by intent (category) from the recorder's event log."""

    _UNCLASSIFIED = "unclassified"
    _MAX_EXAMPLES = 3

    def __init__(self, recorder) -> None:
        self._recorder = recorder

    def top_intents(self, top_n: int = 20) -> list[IntentSummary]:
        """Return the top-N intents by query volume."""
        by_intent: dict[str, list] = defaultdict(list)
        for ev in self._recorder.events():
            intent = ev.category or self._UNCLASSIFIED
            by_intent[intent].append(ev)

        summaries: list[IntentSummary] = []
        for intent, events in by_intent.items():
            examples: list[str] = []
            for ev in events:
                if ev.query not in examples and len(examples) < self._MAX_EXAMPLES:
                    examples.append(ev.query)
            zero = sum(1 for ev in events if ev.result_count == 0)
            avg_ms = sum(ev.duration_ms for ev in events) / len(events)
            summaries.append(
                IntentSummary(
                    intent=intent,
                    count=len(events),
                    example_queries=examples,
                    zero_result_count=zero,
                    avg_duration_ms=avg_ms,
                )
            )
        summaries.sort(key=lambda s: s.count, reverse=True)
        return summaries[:top_n]
