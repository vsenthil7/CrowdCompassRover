"""Availability service — the operational truth layer keyed by venue id.

Combines two separately-sourced facts into one answer the agent and reranker can use:
  * **opening hours** (slow-changing, schedule-based) → is it open at the query time?
  * **live signals** (fast-changing) → is it crowded / shut for an incident right now?

Kept separate from the search index on purpose: opening hours and crowd levels change on a
different cadence than the semantic document, so they live in their own store and are joined
at query time. This mirrors how a production system layers real-time ops data over a slower
search corpus.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.availability.evaluator import AvailabilityStatus, evaluate
from app.availability.hours import OpeningHours, OpenState
from app.livesignals.store import CrowdLevel, LiveSignalStore, ResolvedSignal


@dataclass(frozen=True)
class VenueAvailability:
    """Resolved operational status for one venue at a query instant."""

    venue_id: str
    open_state: OpenState
    is_open: bool
    minutes_to_transition: int | None
    crowd: CrowdLevel
    wait_minutes: int | None
    temporarily_closed: bool
    note: str

    @property
    def effectively_open(self) -> bool:
        """Open per the schedule AND not under a trusted transient closure."""
        return self.is_open and not self.temporarily_closed

    def to_dict(self) -> dict:
        return {
            "venue_id": self.venue_id,
            "open_state": self.open_state.value,
            "is_open": self.is_open,
            "effectively_open": self.effectively_open,
            "minutes_to_transition": self.minutes_to_transition,
            "crowd": self.crowd.value,
            "wait_minutes": self.wait_minutes,
            "temporarily_closed": self.temporarily_closed,
            "note": self.note,
        }


class AvailabilityService:
    """Resolves venue availability by joining opening-hours with live signals."""

    def __init__(
        self,
        *,
        hours: dict[str, OpeningHours] | None = None,
        signals: LiveSignalStore | None = None,
        soon_minutes: int = 30,
    ) -> None:
        self._hours = hours or {}
        self._signals = signals or LiveSignalStore()
        self._soon = soon_minutes

    def set_hours(self, venue_id: str, hours: OpeningHours) -> None:
        self._hours[venue_id] = hours

    @property
    def signals(self) -> LiveSignalStore:
        return self._signals

    def resolve(self, venue_id: str, when: datetime | None = None) -> VenueAvailability:
        """Resolve the combined availability for a venue at ``when`` (default: now, UTC)."""
        now = when or datetime.now(timezone.utc)

        hours = self._hours.get(venue_id)
        if hours is not None:
            status: AvailabilityStatus = evaluate(hours, now, soon_minutes=self._soon)
            open_state, is_open, to_transition = status.state, status.is_open, status.minutes_to_transition
        else:
            # Unknown hours → assume open (don't hide venues we lack data for).
            open_state, is_open, to_transition = OpenState.OPEN, True, None

        live: ResolvedSignal | None = self._signals.resolve(venue_id, now)
        if live is not None:
            crowd, wait, closed, note = live.crowd, live.wait_minutes, live.temporarily_closed, live.note
        else:
            crowd, wait, closed, note = CrowdLevel.UNKNOWN, None, False, ""

        return VenueAvailability(
            venue_id=venue_id,
            open_state=open_state,
            is_open=is_open,
            minutes_to_transition=to_transition,
            crowd=crowd,
            wait_minutes=wait,
            temporarily_closed=closed,
            note=note,
        )

    def crowd_penalty(self, venue_id: str, when: datetime | None = None) -> float:
        """The crowd-based ranking penalty [0,1] for a venue (0 if unknown/fresh-quiet)."""
        now = when or datetime.now(timezone.utc)
        live = self._signals.resolve(venue_id, now)
        return live.crowd_penalty if live is not None else 0.0
