"""Seed the availability service from the fixture corpus.

Gives every fixture venue a plausible opening-hours schedule by category (stadiums open only
on match days, restaurants late, transit hubs nearly always open, etc.) so the time-aware
ranking and the /availability endpoints have realistic data in mock mode. Real deployments
would populate hours from the ingestion feeds instead; this is the mock-mode analogue.
"""
from __future__ import annotations

from app.availability.hours import OpeningHours, TimeWindow
from app.availability.service import AvailabilityService
from app.models.domain import CityEvent, VenueCategory

_ALL_DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _daily(start: str, end: str) -> dict[str, list[TimeWindow]]:
    return {d: [TimeWindow.parse(start, end)] for d in _ALL_DAYS}


def hours_for_category(category: VenueCategory, tz: str = "UTC") -> OpeningHours:
    """A plausible default schedule for a venue category.

    Branches map onto the real VenueCategory values so every branch is reachable.
    """
    name = category.value if hasattr(category, "value") else str(category)
    if name == "restaurant":
        return OpeningHours(tz=tz, weekly=_daily("08:00", "23:30"))
    if name in {"transit", "hospital", "hotel"}:
        # Always-on infrastructure: transport hubs, A&E, hotel reception.
        return OpeningHours(tz=tz, always_open=True)
    if name == "stadium":
        # Matchday windows only (weekend afternoons here as a stand-in).
        return OpeningHours(tz=tz, weekly={"sat": [TimeWindow.parse("12:00", "23:00")],
                                           "sun": [TimeWindow.parse("12:00", "23:00")]})
    if name == "fan_zone":
        return OpeningHours(tz=tz, weekly=_daily("10:00", "00:00"))
    if name == "pop_up_vendor":
        return OpeningHours(tz=tz, weekly=_daily("11:00", "20:00"))
    # currency_exchange, info_kiosk and any future category: standard daytime hours.
    return OpeningHours(tz=tz, weekly=_daily("09:00", "18:00"))


def seed_availability(events: list[CityEvent], *, tz: str = "UTC") -> AvailabilityService:
    """Build an AvailabilityService with category-based hours for each event."""
    svc = AvailabilityService()
    for ev in events:
        svc.set_hours(ev.id, hours_for_category(ev.category, tz=tz))
    return svc
