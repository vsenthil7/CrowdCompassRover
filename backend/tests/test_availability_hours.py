"""Tests for the opening-hours model and availability evaluator."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.availability.hours import (
    OpeningHours,
    OpenState,
    TimeWindow,
    parse_hhmm,
)
from app.availability.evaluator import evaluate, is_open_at


# --- parse_hhmm ---

def test_parse_hhmm_basic():
    assert parse_hhmm("00:00") == 0
    assert parse_hhmm("09:30") == 9 * 60 + 30
    assert parse_hhmm("23:59") == 23 * 60 + 59
    assert parse_hhmm("24:00") == 24 * 60


@pytest.mark.parametrize("bad", ["9", "9:00:00", "25:00", "12:60", "ab:cd"])
def test_parse_hhmm_rejects_bad(bad):
    with pytest.raises(ValueError):
        parse_hhmm(bad)


# --- TimeWindow ---

def test_window_validates_range():
    with pytest.raises(ValueError):
        TimeWindow(-1, 60)
    with pytest.raises(ValueError):
        TimeWindow(0, 24 * 60 + 1)


def test_window_contains_normal():
    w = TimeWindow.parse("09:00", "17:00")
    assert not w.overnight
    assert w.contains(parse_hhmm("09:00"))
    assert w.contains(parse_hhmm("16:59"))
    assert not w.contains(parse_hhmm("17:00"))
    assert not w.contains(parse_hhmm("08:59"))


def test_window_contains_overnight():
    w = TimeWindow.parse("20:00", "02:00")
    assert w.overnight
    assert w.contains(parse_hhmm("23:00"))
    assert w.contains(parse_hhmm("01:00"))
    assert not w.contains(parse_hhmm("12:00"))


def test_window_minutes_until_open_and_close():
    w = TimeWindow.parse("09:00", "17:00")
    assert w.minutes_until_open(parse_hhmm("08:00")) == 60
    assert w.minutes_until_open(parse_hhmm("10:00")) is None  # already open
    assert w.minutes_until_open(parse_hhmm("18:00")) is None  # past, today
    assert w.minutes_until_close(parse_hhmm("16:30")) == 30
    assert w.minutes_until_close(parse_hhmm("08:00")) is None  # not open


def test_window_minutes_until_close_overnight():
    w = TimeWindow.parse("20:00", "02:00")
    # at 23:00, closes at 02:00 next day = 3h
    assert w.minutes_until_close(parse_hhmm("23:00")) == 3 * 60
    # at 01:00 (in the spill), closes in 60 min
    assert w.minutes_until_close(parse_hhmm("01:00")) == 60


# --- evaluator ---

_ALL = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _daily(start, end):
    return {d: [TimeWindow.parse(start, end)] for d in _ALL}


def test_always_open():
    h = OpeningHours(always_open=True)
    s = evaluate(h, datetime(2026, 6, 2, 3, 0, tzinfo=timezone.utc))
    assert s.state is OpenState.OPEN
    assert s.is_open
    assert s.minutes_to_transition is None
    assert s.label == "open"


def test_open_during_window():
    h = OpeningHours(tz="UTC", weekly=_daily("09:00", "17:00"))
    s = evaluate(h, datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc))
    assert s.is_open
    assert s.state is OpenState.OPEN


def test_closing_soon():
    h = OpeningHours(tz="UTC", weekly=_daily("09:00", "17:00"))
    s = evaluate(h, datetime(2026, 6, 2, 16, 40, tzinfo=timezone.utc), soon_minutes=30)
    assert s.is_open
    assert s.state is OpenState.CLOSING_SOON
    assert s.minutes_to_transition == 20


def test_opening_soon():
    h = OpeningHours(tz="UTC", weekly=_daily("09:00", "17:00"))
    s = evaluate(h, datetime(2026, 6, 2, 8, 45, tzinfo=timezone.utc), soon_minutes=30)
    assert not s.is_open
    assert s.state is OpenState.OPENING_SOON
    assert s.minutes_to_transition == 15


def test_closed_far_from_open():
    h = OpeningHours(tz="UTC", weekly=_daily("09:00", "17:00"))
    s = evaluate(h, datetime(2026, 6, 2, 6, 0, tzinfo=timezone.utc))
    assert not s.is_open
    assert s.state is OpenState.CLOSED
    assert s.minutes_to_transition == 180


def test_closed_after_last_window():
    h = OpeningHours(tz="UTC", weekly=_daily("09:00", "17:00"))
    s = evaluate(h, datetime(2026, 6, 2, 20, 0, tzinfo=timezone.utc))
    assert not s.is_open
    assert s.state is OpenState.CLOSED
    assert s.minutes_to_transition is None  # nothing more opens today


def test_timezone_conversion():
    # 13:00 UTC == 15:00 in Madrid (CEST, summer)
    h = OpeningHours(tz="Europe/Madrid", weekly=_daily("11:00", "23:00"))
    assert is_open_at(h, datetime(2026, 6, 2, 13, 0, tzinfo=timezone.utc))
    # 22:00 UTC == 00:00 Madrid -> closed
    assert not is_open_at(h, datetime(2026, 6, 2, 22, 0, tzinfo=timezone.utc))


def test_overnight_spillover_from_previous_day():
    h = OpeningHours(tz="UTC", weekly=_daily("20:00", "02:00"))
    # 01:00 is covered by *yesterday's* window crossing midnight.
    s = evaluate(h, datetime(2026, 6, 2, 1, 0, tzinfo=timezone.utc))
    assert s.is_open
    # 01:50 -> closing soon (10 min to 02:00)
    s2 = evaluate(h, datetime(2026, 6, 2, 1, 50, tzinfo=timezone.utc), soon_minutes=30)
    assert s2.state is OpenState.CLOSING_SOON
    # mid-afternoon closed
    assert not is_open_at(h, datetime(2026, 6, 2, 15, 0, tzinfo=timezone.utc))


def test_overnight_spillover_when_today_has_no_window():
    # Open only Saturday 20:00–02:00. Checked Sunday 01:00: today (Sun) has no window,
    # but Saturday's overnight window still covers Sunday's early hours.
    h = OpeningHours(tz="UTC", weekly={"sat": [TimeWindow.parse("20:00", "02:00")]})
    # 2026-06-07 is a Sunday; 01:00 should be open via Saturday's spillover.
    s = evaluate(h, datetime(2026, 6, 7, 1, 0, tzinfo=timezone.utc), soon_minutes=30)
    assert s.is_open
    assert s.state is OpenState.OPEN
    assert s.minutes_to_transition == 60  # closes at 02:00
    # 01:45 Sunday -> closing soon
    s2 = evaluate(h, datetime(2026, 6, 7, 1, 45, tzinfo=timezone.utc), soon_minutes=30)
    assert s2.state is OpenState.CLOSING_SOON
    # Sunday 12:00 -> closed (no Sunday window, Saturday spill ended at 02:00)
    assert not is_open_at(h, datetime(2026, 6, 7, 12, 0, tzinfo=timezone.utc))


def test_special_date_override_closes():
    h = OpeningHours(tz="UTC", weekly=_daily("09:00", "17:00"), overrides={"2026-06-02": []})
    assert not is_open_at(h, datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc))
    # next day uses the weekly schedule again
    assert is_open_at(h, datetime(2026, 6, 3, 12, 0, tzinfo=timezone.utc))


def test_special_date_override_custom_hours():
    h = OpeningHours(tz="UTC", weekly=_daily("09:00", "17:00"),
                     overrides={"2026-06-02": [TimeWindow.parse("18:00", "22:00")]})
    assert not is_open_at(h, datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc))
    assert is_open_at(h, datetime(2026, 6, 2, 19, 0, tzinfo=timezone.utc))


def test_naive_datetime_treated_as_utc():
    h = OpeningHours(tz="UTC", weekly=_daily("09:00", "17:00"))
    assert is_open_at(h, datetime(2026, 6, 2, 12, 0))  # naive -> UTC


def test_no_schedule_for_day_is_closed():
    h = OpeningHours(tz="UTC", weekly={"sat": [TimeWindow.parse("12:00", "23:00")]})
    # 2026-06-02 is a Tuesday -> no window
    assert not is_open_at(h, datetime(2026, 6, 2, 14, 0, tzinfo=timezone.utc))
    # Saturday 2026-06-06 -> open
    assert is_open_at(h, datetime(2026, 6, 6, 14, 0, tzinfo=timezone.utc))
