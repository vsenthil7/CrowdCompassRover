"""Availability evaluator: turn an ``OpeningHours`` schedule + an instant into a concrete
open/closed status, with "opening soon" / "closing soon" nuance and the next transition.

Correctly handles:
  * timezone conversion (instant → venue-local),
  * special-date overrides (holidays, match-days),
  * overnight windows, including spillover from the *previous* local day
    (a 20:00–02:00 bar is still open at 01:00 today because yesterday's window crosses
    midnight),
  * an always-open (24/7) short-circuit.

Pure and deterministic.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.availability.hours import OpeningHours, OpenState, TimeWindow

DEFAULT_SOON_MINUTES = 30


@dataclass(frozen=True)
class AvailabilityStatus:
    """Resolved availability at an instant."""

    state: OpenState
    is_open: bool
    minutes_to_transition: int | None  # to close (if open) or to open (if closed)

    @property
    def label(self) -> str:
        return self.state.value


def _minute_of_day(local_dt: datetime) -> int:
    return local_dt.hour * 60 + local_dt.minute


def evaluate(
    hours: OpeningHours,
    when: datetime,
    *,
    soon_minutes: int = DEFAULT_SOON_MINUTES,
) -> AvailabilityStatus:
    """Compute the availability status of a schedule at instant ``when``."""
    if hours.always_open:
        return AvailabilityStatus(OpenState.OPEN, True, None)

    local = hours.to_local(when)
    minute = _minute_of_day(local)

    # 1) Is it open right now? Check today's windows, plus yesterday's overnight spillover.
    today_windows = hours.windows_for(local)
    for w in today_windows:
        if w.contains(minute):
            close_in = w.minutes_until_close(minute)
            state = (
                OpenState.CLOSING_SOON
                if close_in is not None and close_in <= soon_minutes
                else OpenState.OPEN
            )
            return AvailabilityStatus(state, True, close_in)

    # Yesterday's overnight window may still cover the early hours of today.
    yesterday = hours.windows_for(local - timedelta(days=1))
    for w in yesterday:
        if w.overnight and minute < w.end:
            close_in = w.end - minute
            state = OpenState.CLOSING_SOON if close_in <= soon_minutes else OpenState.OPEN
            return AvailabilityStatus(state, True, close_in)

    # 2) Closed now — find the soonest upcoming opening today.
    soonest_open: int | None = None
    for w in today_windows:
        until = w.minutes_until_open(minute)
        if until is not None and (soonest_open is None or until < soonest_open):
            soonest_open = until

    if soonest_open is not None:
        state = OpenState.OPENING_SOON if soonest_open <= soon_minutes else OpenState.CLOSED
        return AvailabilityStatus(state, False, soonest_open)

    return AvailabilityStatus(OpenState.CLOSED, False, None)


def is_open_at(hours: OpeningHours, when: datetime) -> bool:
    """Convenience boolean: is the venue open at ``when``?"""
    return evaluate(hours, when).is_open
