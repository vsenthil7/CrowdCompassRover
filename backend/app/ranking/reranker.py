"""Re-ranking layer applying business signals on top of hybrid relevance.

Hybrid search gives a relevance score; real products then re-rank with signals that matter
operationally: prefer open venues, boost closer results, gently boost higher-capacity
matchday venues, and demote items missing requested attributes. Weights are explicit and
tunable. Reranking is pure and deterministic, so it is fully testable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.models.domain import QueryPlan, ScoredEvent


class _Availability(Protocol):
    open_state: object
    temporarily_closed: bool


class AvailabilityResolver(Protocol):
    """Minimal interface the reranker needs from an availability source."""

    def resolve(self, venue_id: str, when: datetime | None = ...) -> _Availability: ...
    def crowd_penalty(self, venue_id: str, when: datetime | None = ...) -> float: ...


@dataclass
class RerankWeights:
    """Tunable weights for re-ranking signals."""

    relevance: float = 1.0
    open_now_boost: float = 0.15
    proximity_boost: float = 0.20
    capacity_boost: float = 0.05
    proximity_scale_km: float = 10.0
    # Availability-aware signals (time + live crowd). Applied only when an
    # availability resolver is supplied to rerank(); otherwise inert, so the
    # static open_now path is unchanged.
    closing_soon_penalty: float = 0.10
    crowd_penalty: float = 0.20
    temporarily_closed_penalty: float = 0.50


def _proximity_factor(distance_km: float | None, scale: float) -> float:
    """Map distance to a [0,1] boost: closer is higher; None is neutral 0."""
    if distance_km is None:
        return 0.0
    return max(0.0, 1.0 - min(distance_km, scale) / scale)


def rerank(
    plan: QueryPlan,
    results: list[ScoredEvent],
    weights: RerankWeights | None = None,
    availability: "AvailabilityResolver | None" = None,
    when: "datetime | None" = None,
) -> list[ScoredEvent]:
    """Return results re-ordered by a composite operational score.

    When an ``availability`` resolver is supplied, time-aware signals refine the static
    ``open_now`` boost: venues closing soon are gently penalised, crowded venues are demoted
    in proportion to (freshness-decayed) crowd level, and venues under a trusted transient
    closure are heavily penalised. Without a resolver, behaviour is unchanged.
    """
    w = weights or RerankWeights()
    rescored: list[tuple[float, ScoredEvent]] = []
    max_capacity = max((r.event.capacity or 0) for r in results) if results else 0

    for r in results:
        score = w.relevance * r.score
        if r.event.open_now:
            score += w.open_now_boost
        score += w.proximity_boost * _proximity_factor(r.distance_km, w.proximity_scale_km)
        if max_capacity > 0 and r.event.capacity:
            score += w.capacity_boost * (r.event.capacity / max_capacity)

        if availability is not None:
            av = availability.resolve(r.event.id, when)
            if av.temporarily_closed:
                score -= w.temporarily_closed_penalty
            if av.open_state.value == "closing_soon":
                score -= w.closing_soon_penalty
            score -= w.crowd_penalty * availability.crowd_penalty(r.event.id, when)

        rescored.append((round(score, 6), r))

    rescored.sort(key=lambda pair: (pair[0], -(pair[1].distance_km or 0)), reverse=True)
    # Reflect the reranked score back onto the ScoredEvent for transparency.
    out: list[ScoredEvent] = []
    for new_score, r in rescored:
        out.append(ScoredEvent(event=r.event, score=new_score, distance_km=r.distance_km))
    return out
