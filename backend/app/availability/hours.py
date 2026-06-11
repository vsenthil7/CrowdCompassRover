"""Opening-hours model for city venues.

The product's headline queries — "nearest *open* halal restaurant *now*", "cheapest route to
the stadium *now*" — are time-sensitive, but the base event model only carried a static
``open_now`` boolean that could never actually reflect the query time. This module replaces
that with a real, timezone-aware weekly schedule plus special-date overrides (a stadium open
only on match days; a restaurant closed on a public holiday), and an evaluator that answers
"is this open at instant X?" together with "opening soon" / "closing soon" nuance.

Pure data + pure functions: no I/O, no globals, fully deterministic and unit-testable. Times
are minutes-since-midnight in the venue's local timezone; the evaluator takes an aware
``datetime`` and converts to the venue's zone.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone, tzinfo
from enum import Enum
from zoneinfo import ZoneInfo


class OpenState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    OPENING_SOON = "opening_soon"   # closed now, opens within the soon-window
    CLOSING_SOON = "closing_soon"   # open now, closes within the soon-window


# Weekday convention matches Python's datetime.weekday(): Mon=0 … Sun=6.
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def parse_hhmm(value: str) -> int:
    """Parse 'HH:MM' (24h) into minutes since midnight. '24:00' means end-of-day."""
    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"invalid time: {value!r}")
    h, m = int(parts[0]), int(parts[1])
    if h == 24 and m == 0:
        return 24 * 60
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"time out of range: {value!r}")
    return h * 60 + m


@dataclass(frozen=True)
class TimeWindow:
    """A single open interval within a day, in local minutes-since-midnight.

    Supports overnight windows (e.g. 20:00–02:00) by allowing ``end <= start``,
    interpreted as crossing midnight into the next day.
    """

    start: int
    end: int

    def __post_init__(self) -> None:
        for v in (self.start, self.end):
            if not (0 <= v <= 24 * 60):
                raise ValueError(f"window minute out of range: {v}")

    @property
    def overnight(self) -> bool:
        return self.end <= self.start

    def contains(self, minute: int) -> bool:
        """Whether a local minute-of-day falls inside this window."""
        if self.overnight:
            return minute >= self.start or minute < self.end
        return self.start <= minute < self.end

    def minutes_until_open(self, minute: int) -> int | None:
        """Minutes from ``minute`` until this window next opens today (None if open/none)."""
        if self.contains(minute):
            return None
        if minute < self.start:
            return self.start - minute
        return None

    def minutes_until_close(self, minute: int) -> int | None:
        """Minutes until this window closes, if currently inside it."""
        if not self.contains(minute):
            return None
        if self.overnight:
            # close is tomorrow's self.end
            return (24 * 60 - minute) + self.end if minute >= self.start else self.end - minute
        return self.end - minute

    @classmethod
    def parse(cls, start: str, end: str) -> "TimeWindow":
        return cls(parse_hhmm(start), parse_hhmm(end))


@dataclass
class OpeningHours:
    """A weekly schedule with optional special-date overrides.

    ``weekly`` maps a weekday key (mon..sun) to a list of windows. ``overrides`` maps an ISO
    date (YYYY-MM-DD) to a list of windows that *replace* the weekly schedule for that date
    (an empty list = closed all day, e.g. a holiday). ``always_open`` short-circuits to 24/7.
    """

    tz: str = "UTC"
    weekly: dict[str, list[TimeWindow]] = field(default_factory=dict)
    overrides: dict[str, list[TimeWindow]] = field(default_factory=dict)
    always_open: bool = False

    def _zone(self) -> tzinfo:
        try:
            return ZoneInfo(self.tz)
        except Exception:  # pragma: no cover - defensive; invalid tz falls back to UTC
            return timezone.utc

    def windows_for(self, local_dt: datetime) -> list[TimeWindow]:
        """The effective windows for the local date (override beats weekly)."""
        iso = local_dt.date().isoformat()
        if iso in self.overrides:
            return self.overrides[iso]
        return self.weekly.get(WEEKDAYS[local_dt.weekday()], [])

    def to_local(self, when: datetime) -> datetime:
        """Convert an instant to the venue's local timezone (assume UTC if naive)."""
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return when.astimezone(self._zone())
