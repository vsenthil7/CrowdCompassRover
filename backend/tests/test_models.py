"""Tests for domain models and fixtures."""
from __future__ import annotations

from app.data.fixtures import HOST_CITIES, load_fixture_events
from app.models.domain import CityEvent, GeoPoint, VenueCategory


def test_fixtures_load_and_cover_cities():
    events = load_fixture_events()
    assert len(events) >= 15
    cities = {e.city for e in events}
    assert set(HOST_CITIES) <= cities


def test_fixtures_have_categories():
    events = load_fixture_events()
    cats = {e.category for e in events}
    assert VenueCategory.STADIUM in cats
    assert VenueCategory.RESTAURANT in cats
    assert VenueCategory.CURRENCY_EXCHANGE in cats


def test_city_event_text_blob():
    ev = CityEvent(
        id="x",
        name="Test Venue",
        category=VenueCategory.STADIUM,
        city="Nowhere",
        description="A Big Place",
        location=GeoPoint(lat=0, lon=0),
        tags=["alpha", "beta"],
    )
    blob = ev.text_blob()
    assert "test venue" in blob
    assert "alpha" in blob
    assert blob == blob.lower()


def test_geopoint_validation_bounds():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        GeoPoint(lat=200, lon=0)
