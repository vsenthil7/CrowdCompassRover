"""Tests for the mock planner and language detection."""
from __future__ import annotations

import pytest

from app.agent.planner import MockPlanner, detect_language
from app.models.domain import GeoPoint, VenueCategory


@pytest.fixture
def planner() -> MockPlanner:
    return MockPlanner()


def test_detect_language_english_default():
    assert detect_language(["where", "is", "the", "stadium"]) == "en"


def test_detect_language_no_markers_defaults_english():
    assert detect_language(["xyz", "qqq"]) == "en"


def test_detect_language_spanish():
    assert detect_language(["donde", "esta", "el", "estadio"]) == "es"


def test_detect_language_french():
    assert detect_language(["ou", "est", "le", "stade"]) == "fr"


def test_detect_language_english_wins_tie():
    # 'open' and 'route' are English markers; 'estadio' Spanish. English should win/keep.
    assert detect_language(["open", "route", "estadio"]) == "en"


async def test_plan_english_stadium(planner):
    plan = await planner.plan("where is the stadium", None, 5)
    assert plan.detected_language == "en"
    assert plan.filters.category == VenueCategory.STADIUM
    assert plan.top_k == 5


async def test_plan_spanish_halal_open(planner):
    plan = await planner.plan("comida halal abierto ahora", None, 3)
    assert plan.detected_language == "es"
    assert plan.filters.category == VenueCategory.RESTAURANT
    assert plan.filters.halal is True
    assert plan.filters.open_now is True


async def test_plan_city_word_boundary_not_in_halal(planner):
    # 'halal' must NOT trigger 'la' -> Los Angeles.
    plan = await planner.plan("halal food", None, 5)
    assert plan.filters.city is None


async def test_plan_city_detected(planner):
    plan = await planner.plan("stadium in mexico city", None, 5)
    assert plan.filters.city == "Mexico City"


async def test_plan_vegetarian(planner):
    plan = await planner.plan("vegetarian restaurant", None, 5)
    assert plan.filters.vegetarian is True


async def test_plan_near_with_location(planner):
    loc = GeoPoint(lat=40.0, lon=-74.0)
    plan = await planner.plan("nearest transit", loc, 5)
    assert plan.filters.near == loc
    assert plan.filters.max_distance_km == 25.0
    assert plan.filters.category == VenueCategory.TRANSIT


async def test_plan_near_without_location_no_geo(planner):
    plan = await planner.plan("nearest transit", None, 5)
    assert plan.filters.near is None


async def test_plan_currency_exchange_french(planner):
    plan = await planner.plan("ou change maintenant", None, 5)
    assert plan.detected_language == "fr"
    assert plan.filters.category == VenueCategory.CURRENCY_EXCHANGE
    assert plan.filters.open_now is True


async def test_plan_normalization_translates_tokens(planner):
    plan = await planner.plan("estadio", None, 5)
    assert "stadium" in plan.normalized_query
