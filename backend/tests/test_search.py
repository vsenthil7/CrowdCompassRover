"""Tests for the hybrid ranker and mock search provider."""
from __future__ import annotations

import pytest

from app.models.domain import GeoPoint, QueryPlan, SearchFilters, VenueCategory
from app.services.hybrid import hybrid_rank
from app.services.mock_search import MockSearchProvider


def _plan(**kw) -> QueryPlan:
    base = dict(
        original_query="q",
        detected_language="en",
        normalized_query="stadium",
        semantic_text="stadium",
        filters=SearchFilters(),
        top_k=10,
    )
    base.update(kw)
    return QueryPlan(**base)


@pytest.fixture
def provider() -> MockSearchProvider:
    return MockSearchProvider()


async def test_list_indices(provider):
    assert await provider.list_indices() == ["cc-city-events"]


async def test_get_mappings(provider):
    m = await provider.get_mappings("cc-city-events")
    assert m["properties"]["embedding"]["type"] == "dense_vector"


async def test_get_mappings_unknown_index(provider):
    with pytest.raises(KeyError):
        await provider.get_mappings("nope")


async def test_search_stadium_returns_stadiums(provider):
    plan = _plan(normalized_query="stadium", semantic_text="stadium football match")
    results = await provider.search(plan)
    assert results
    assert any(r.event.category == VenueCategory.STADIUM for r in results)


async def test_search_respects_category_filter(provider):
    plan = _plan(filters=SearchFilters(category=VenueCategory.CURRENCY_EXCHANGE))
    results = await provider.search(plan)
    assert results
    assert all(r.event.category == VenueCategory.CURRENCY_EXCHANGE for r in results)


async def test_search_open_now_filter(provider):
    plan = _plan(filters=SearchFilters(open_now=True))
    results = await provider.search(plan)
    assert all(r.event.open_now for r in results)


async def test_search_halal_filter(provider):
    plan = _plan(filters=SearchFilters(halal=True))
    results = await provider.search(plan)
    assert results
    assert all(r.event.halal for r in results)


async def test_search_vegetarian_filter(provider):
    plan = _plan(filters=SearchFilters(vegetarian=True))
    results = await provider.search(plan)
    assert all(r.event.vegetarian for r in results)


async def test_search_wheelchair_filter(provider):
    plan = _plan(filters=SearchFilters(wheelchair_accessible=True))
    results = await provider.search(plan)
    assert all(r.event.wheelchair_accessible for r in results)


async def test_search_city_filter(provider):
    plan = _plan(filters=SearchFilters(city="Mexico City"))
    results = await provider.search(plan)
    assert results
    assert all(r.event.city == "Mexico City" for r in results)


async def test_search_geo_distance_filter_and_distance_set(provider):
    near = GeoPoint(lat=40.8135, lon=-74.0745)  # MetLife
    plan = _plan(filters=SearchFilters(near=near, max_distance_km=5.0))
    results = await provider.search(plan)
    assert results
    for r in results:
        assert r.distance_km is not None
        assert r.distance_km <= 5.0


async def test_search_geo_excludes_far(provider):
    near = GeoPoint(lat=40.8135, lon=-74.0745)
    plan = _plan(filters=SearchFilters(near=near, max_distance_km=1.0))
    results = await provider.search(plan)
    # MetLife is within 1km of itself; Mexico City venues must be excluded.
    assert all(r.event.city == "New York" for r in results)


async def test_search_top_k_limits(provider):
    plan = _plan(top_k=2)
    results = await provider.search(plan)
    assert len(results) <= 2


async def test_hybrid_empty_query_terms():
    plan = _plan(normalized_query="", semantic_text="")
    provider = MockSearchProvider()
    results = await provider.search(plan)
    # No keyword signal -> still returns vector-ranked docs.
    assert isinstance(results, list)


def test_hybrid_rank_no_matching_filter_returns_empty():
    from app.data.fixtures import load_fixture_events

    events = load_fixture_events()
    plan = _plan(filters=SearchFilters(city="Atlantis"))
    assert hybrid_rank(plan, events) == []


def test_provider_events_property(provider):
    assert len(provider.events) >= 15


def test_provider_accepts_custom_events():
    from app.data.fixtures import load_fixture_events

    evs = load_fixture_events()[:3]
    p = MockSearchProvider(events=evs)
    assert len(p.events) == 3


def test_hybrid_precomputed_embedding_branch():
    from app.core.embedding import embed
    from app.data.fixtures import load_fixture_events

    events = load_fixture_events()
    for e in events:
        e.embedding = embed(e.text_blob())
    plan = _plan()
    ranked = hybrid_rank(plan, events)
    assert ranked
