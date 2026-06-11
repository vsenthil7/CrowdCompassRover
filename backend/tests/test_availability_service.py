"""Tests for live signals, the availability service, seeding, and reranker integration."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.availability.hours import OpeningHours, OpenState, TimeWindow
from app.availability.service import AvailabilityService, VenueAvailability
from app.availability.seed import hours_for_category, seed_availability
from app.livesignals.store import (
    CrowdLevel,
    LiveSignal,
    LiveSignalStore,
    ResolvedSignal,
)
from app.ranking.reranker import RerankWeights, rerank
from app.models.domain import (
    CityEvent,
    GeoPoint,
    QueryPlan,
    ScoredEvent,
    SearchFilters,
    VenueCategory,
)

NOW = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)
_ALL = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _daily(s, e):
    return {d: [TimeWindow.parse(s, e)] for d in _ALL}


# --- LiveSignalStore ---

def test_signal_store_rejects_bad_ttl():
    with pytest.raises(ValueError):
        LiveSignalStore(ttl_seconds=0)


def test_report_and_resolve_fresh():
    store = LiveSignalStore(ttl_seconds=3600)
    store.report(LiveSignal("v1", NOW - timedelta(minutes=5), crowd=CrowdLevel.BUSY, wait_minutes=20))
    r = store.resolve("v1", NOW)
    assert r is not None
    assert r.crowd is CrowdLevel.BUSY
    assert r.wait_minutes == 20
    assert 0.9 < r.freshness <= 1.0
    assert r.crowd_penalty > 0


def test_resolve_unknown_returns_none():
    store = LiveSignalStore()
    assert store.resolve("nope", NOW) is None


def test_fully_stale_signal_resolves_none():
    store = LiveSignalStore(ttl_seconds=600)
    store.report(LiveSignal("v1", NOW - timedelta(hours=2), crowd=CrowdLevel.PACKED))
    assert store.resolve("v1", NOW) is None


def test_freshness_linear():
    store = LiveSignalStore(ttl_seconds=1000)
    assert store.freshness(0) == 1.0
    assert store.freshness(500) == 0.5
    assert store.freshness(1000) == 0.0
    assert store.freshness(2000) == 0.0


def test_low_freshness_demotes_to_unknown_crowd():
    # trust_floor default 0.25; at age 0.9*ttl freshness=0.1 < floor -> crowd unknown
    store = LiveSignalStore(ttl_seconds=1000, trust_floor=0.25)
    store.report(LiveSignal("v1", NOW - timedelta(seconds=900), crowd=CrowdLevel.PACKED, temporarily_closed=True))
    r = store.resolve("v1", NOW)
    assert r is not None
    assert r.crowd is CrowdLevel.UNKNOWN
    assert r.temporarily_closed is False  # closure not trusted when stale-ish
    assert r.crowd_penalty == 0.0


def test_report_keeps_latest_by_observed_at():
    store = LiveSignalStore()
    store.report(LiveSignal("v1", NOW - timedelta(minutes=1), crowd=CrowdLevel.PACKED))
    store.report(LiveSignal("v1", NOW - timedelta(minutes=10), crowd=CrowdLevel.QUIET))  # older, ignored
    r = store.resolve("v1", NOW)
    assert r.crowd is CrowdLevel.PACKED


def test_signal_age_handles_naive_datetimes():
    store = LiveSignalStore()
    sig = LiveSignal("v1", datetime(2026, 6, 2, 11, 0))  # naive
    assert sig.age_seconds(datetime(2026, 6, 2, 12, 0)) == 3600.0


def test_prune_stale():
    store = LiveSignalStore(ttl_seconds=600)
    store.report(LiveSignal("fresh", NOW - timedelta(minutes=1), crowd=CrowdLevel.QUIET))
    store.report(LiveSignal("old", NOW - timedelta(hours=2), crowd=CrowdLevel.BUSY))
    assert store.count() == 2
    removed = store.prune_stale(NOW)
    assert removed == 1
    assert store.count() == 1


def test_resolved_signal_penalty_scales_with_freshness():
    full = ResolvedSignal(crowd=CrowdLevel.PACKED, wait_minutes=None, temporarily_closed=False, freshness=1.0)
    half = ResolvedSignal(crowd=CrowdLevel.PACKED, wait_minutes=None, temporarily_closed=False, freshness=0.5)
    assert full.crowd_penalty == 1.0
    assert half.crowd_penalty == 0.5


# --- AvailabilityService ---

def test_service_unknown_hours_assumes_open():
    svc = AvailabilityService()
    av = svc.resolve("ghost", NOW)
    assert av.is_open
    assert av.open_state is OpenState.OPEN
    assert av.crowd is CrowdLevel.UNKNOWN


def test_service_combines_hours_and_signals():
    svc = AvailabilityService(hours={"v1": OpeningHours(tz="UTC", weekly=_daily("09:00", "17:00"))})
    svc.signals.report(LiveSignal("v1", NOW - timedelta(minutes=2), crowd=CrowdLevel.PACKED, wait_minutes=45))
    av = svc.resolve("v1", NOW)
    assert av.is_open
    assert av.crowd is CrowdLevel.PACKED
    assert av.wait_minutes == 45
    assert av.effectively_open  # open and not closed


def test_service_set_hours():
    svc = AvailabilityService()
    svc.set_hours("v1", OpeningHours(tz="UTC", weekly=_daily("09:00", "17:00")))
    assert svc.resolve("v1", datetime(2026, 6, 2, 3, 0, tzinfo=timezone.utc)).is_open is False


def test_service_transient_closure_makes_not_effectively_open():
    svc = AvailabilityService(hours={"v1": OpeningHours(always_open=True)})
    svc.signals.report(LiveSignal("v1", NOW - timedelta(minutes=1), temporarily_closed=True, note="incident"))
    av = svc.resolve("v1", NOW)
    assert av.is_open  # schedule says open (24/7)
    assert av.temporarily_closed
    assert not av.effectively_open
    assert av.note == "incident"


def test_service_crowd_penalty():
    svc = AvailabilityService()
    svc.signals.report(LiveSignal("v1", NOW - timedelta(minutes=1), crowd=CrowdLevel.BUSY))
    assert svc.crowd_penalty("v1", NOW) > 0
    assert svc.crowd_penalty("unknown", NOW) == 0.0


def test_venue_availability_to_dict():
    av = VenueAvailability(
        venue_id="v1", open_state=OpenState.OPEN, is_open=True, minutes_to_transition=30,
        crowd=CrowdLevel.QUIET, wait_minutes=None, temporarily_closed=False, note="",
    )
    d = av.to_dict()
    assert d["venue_id"] == "v1"
    assert d["open_state"] == "open"
    assert d["effectively_open"] is True


def test_service_resolve_defaults_to_now(monkeypatch):
    # resolve() with when=None uses current time; just assert it runs and is open for 24/7.
    svc = AvailabilityService(hours={"v1": OpeningHours(always_open=True)})
    av = svc.resolve("v1")
    assert av.is_open


def test_service_crowd_penalty_defaults_to_now():
    svc = AvailabilityService()
    svc.signals.report(LiveSignal("v1", datetime.now(timezone.utc), crowd=CrowdLevel.BUSY))
    assert svc.crowd_penalty("v1") > 0


# --- seed ---

@pytest.mark.parametrize(
    "cat_name,expect_always",
    [
        ("restaurant", False),
        ("transit", True),
        ("hospital", True),
        ("hotel", True),
        ("stadium", False),
        ("fan_zone", False),
        ("pop_up_vendor", False),
        ("currency_exchange", False),
        ("info_kiosk", False),
    ],
)
def test_hours_for_category_shapes(cat_name, expect_always):
    cat = _category(cat_name)
    h = hours_for_category(cat)
    assert h.always_open is expect_always


def test_hours_for_category_default_branch():
    # A category with no special rule (e.g. currency_exchange) falls into the default schedule.
    h = hours_for_category(_category("currency_exchange"))
    assert h.always_open is False
    assert "mon" in h.weekly


def test_seed_availability_covers_all_events():
    events = [
        _event("e1", "restaurant"),
        _event("e2", "transit"),
    ]
    svc = seed_availability(events)
    assert svc.resolve("e1", NOW) is not None
    assert svc.resolve("e2", NOW).is_open  # transit 24/7


# --- reranker integration ---

def _plan():
    return QueryPlan(original_query="q", detected_language="en", normalized_query="q",
                     semantic_text="q", filters=SearchFilters(), top_k=5)


def test_rerank_without_availability_unchanged():
    results = [
        ScoredEvent(event=_event("a", "restaurant"), score=1.0, distance_km=1.0),
        ScoredEvent(event=_event("b", "restaurant"), score=0.5, distance_km=1.0),
    ]
    out = rerank(_plan(), results)
    assert [r.event.id for r in out] == ["a", "b"]


def test_rerank_demotes_crowded_venue():
    svc = AvailabilityService()
    svc.signals.report(LiveSignal("a", NOW - timedelta(minutes=1), crowd=CrowdLevel.PACKED))
    results = [
        ScoredEvent(event=_event("a", "restaurant"), score=1.0, distance_km=1.0),
        ScoredEvent(event=_event("b", "restaurant"), score=1.0, distance_km=1.0),
    ]
    out = rerank(_plan(), results, RerankWeights(), availability=svc, when=NOW)
    assert [r.event.id for r in out][0] == "b"  # quiet b beats packed a


def test_rerank_penalises_temporarily_closed():
    svc = AvailabilityService(hours={"a": OpeningHours(always_open=True)})
    svc.signals.report(LiveSignal("a", NOW - timedelta(minutes=1), temporarily_closed=True))
    results = [
        ScoredEvent(event=_event("a", "restaurant"), score=1.0, distance_km=1.0),
        ScoredEvent(event=_event("b", "restaurant"), score=0.7, distance_km=1.0),
    ]
    out = rerank(_plan(), results, RerankWeights(), availability=svc, when=NOW)
    assert out[0].event.id == "b"


def test_rerank_penalises_closing_soon():
    svc = AvailabilityService(hours={"a": OpeningHours(tz="UTC", weekly=_daily("09:00", "17:00"))})
    # NOW=12:00 is mid-window (open, not closing soon) → use a time near close.
    when = datetime(2026, 6, 2, 16, 50, tzinfo=timezone.utc)  # 10 min to close
    results = [
        ScoredEvent(event=_event("a", "restaurant"), score=1.0, distance_km=1.0),
        ScoredEvent(event=_event("b", "restaurant"), score=0.95, distance_km=1.0),
    ]
    out = rerank(_plan(), results, RerankWeights(closing_soon_penalty=0.2), availability=svc, when=when)
    assert out[0].event.id == "b"


# --- helpers ---

def _category(name: str) -> VenueCategory:
    for c in VenueCategory:
        if c.value == name:
            return c
    # Fall back to the first category for names not in the enum (exercises default branch).
    return list(VenueCategory)[0]


def _event(eid: str, cat_name: str) -> CityEvent:
    return CityEvent(
        id=eid, name=eid, category=_category(cat_name), city="Madrid",
        description="x", location=GeoPoint(lat=40.4, lon=-3.7), open_now=True,
    )
