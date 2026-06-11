"""Tests for answerers and the Gemini client/planner/answerer."""
from __future__ import annotations

import json

import httpx
import pytest

from app.agent.answerer import MockAnswerer
from app.agent.gemini_client import GeminiClient, GeminiError
from app.agent.gemini_planner import GeminiAnswerer, GeminiPlanner
from app.models.domain import (
    CityEvent,
    GeoPoint,
    QueryPlan,
    ScoredEvent,
    SearchFilters,
    VenueCategory,
)


def _plan(lang="en", **kw) -> QueryPlan:
    base = dict(
        original_query="where halal",
        detected_language=lang,
        normalized_query="halal",
        semantic_text="halal",
        filters=SearchFilters(),
        top_k=5,
    )
    base.update(kw)
    return QueryPlan(**base)


def _event(eid="e1", open_now=True) -> CityEvent:
    return CityEvent(
        id=eid,
        name="Halal Place",
        category=VenueCategory.RESTAURANT,
        city="New York",
        description="d",
        location=GeoPoint(lat=40.0, lon=-74.0),
        open_now=open_now,
        halal=True,
    )


def _hit(eid="e1", dist=None, open_now=True) -> ScoredEvent:
    return ScoredEvent(event=_event(eid, open_now), score=0.9, distance_km=dist)


# --- MockAnswerer ---


async def test_mock_answerer_no_results_english():
    ans = await MockAnswerer().answer(_plan(), [])
    assert ans.language == "en"
    assert ans.citations == []
    assert "could not find" in ans.answer.lower()


async def test_mock_answerer_no_results_spanish():
    ans = await MockAnswerer().answer(_plan(lang="es"), [])
    assert ans.language == "es"


async def test_mock_answerer_unknown_language_falls_back_to_en():
    ans = await MockAnswerer().answer(_plan(lang="zz"), [_hit()])
    assert ans.language == "en"


async def test_mock_answerer_lists_results_with_distance():
    ans = await MockAnswerer().answer(_plan(), [_hit(dist=2.34)])
    assert "Halal Place" in ans.answer
    assert "2.3 km" in ans.answer
    assert len(ans.citations) == 1


async def test_mock_answerer_closed_status():
    ans = await MockAnswerer().answer(_plan(), [_hit(open_now=False)])
    assert "closed" in ans.answer


# --- GeminiClient ---


def _transport(handler):
    return httpx.MockTransport(handler)


async def test_gemini_generate_text():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "hello "}, {"text": "world"}]}}]},
        )

    c = GeminiClient("k", transport=_transport(handler))
    assert await c.generate_text("sys", "user") == "hello world"
    await c.aclose()


async def test_gemini_generate_json_strips_fences():
    def handler(request: httpx.Request) -> httpx.Response:
        text = "```json\n{\"a\": 1}\n```"
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})

    c = GeminiClient("k", transport=_transport(handler))
    assert await c.generate_json("s", "u") == {"a": 1}
    await c.aclose()


async def test_gemini_error_envelope():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": {"message": "bad"}})

    c = GeminiClient("k", transport=_transport(handler))
    with pytest.raises(GeminiError):
        await c.generate_text("s", "u")
    await c.aclose()


async def test_gemini_no_candidates():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": []})

    c = GeminiClient("k", transport=_transport(handler))
    with pytest.raises(GeminiError):
        await c.generate_text("s", "u")
    await c.aclose()


# --- GeminiPlanner ---


async def test_gemini_planner_success():
    def handler(request: httpx.Request) -> httpx.Response:
        out = {
            "detected_language": "fr",
            "normalized_query": "stadium",
            "semantic_text": "stadium",
            "filters": {"category": "stadium", "open_now": True, "near": True},
        }
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(out)}]}}]},
        )

    c = GeminiClient("k", transport=_transport(handler))
    planner = GeminiPlanner(c)
    plan = await planner.plan("ou est le stade", GeoPoint(lat=1, lon=2), 5)
    assert plan.detected_language == "fr"
    assert plan.filters.category == VenueCategory.STADIUM
    assert plan.filters.near is not None
    await c.aclose()


async def test_gemini_planner_invalid_category_ignored():
    def handler(request: httpx.Request) -> httpx.Response:
        out = {"detected_language": "en", "normalized_query": "x", "filters": {"category": "bogus"}}
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(out)}]}}]})

    c = GeminiClient("k", transport=_transport(handler))
    plan = await GeminiPlanner(c).plan("x", None, 5)
    assert plan.filters.category is None
    await c.aclose()


async def test_gemini_planner_falls_back_on_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={})

    c = GeminiClient("k", transport=_transport(handler))
    plan = await GeminiPlanner(c).plan("where is the stadium", None, 5)
    # Fallback mock planner still classifies stadium.
    assert plan.filters.category == VenueCategory.STADIUM
    await c.aclose()


# --- GeminiAnswerer ---


async def test_gemini_answerer_success():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "Try Halal Place."}]}}]})

    c = GeminiClient("k", transport=_transport(handler))
    ans = await GeminiAnswerer(c).answer(_plan(), [_hit()])
    assert "Halal Place" in ans.answer
    assert ans.citations[0].event_id == "e1"
    await c.aclose()


async def test_gemini_answerer_no_results_uses_fallback():
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - not called
        return httpx.Response(200, json={})

    c = GeminiClient("k", transport=_transport(handler))
    ans = await GeminiAnswerer(c).answer(_plan(), [])
    assert ans.citations == []
    await c.aclose()


async def test_gemini_answerer_falls_back_on_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={})

    c = GeminiClient("k", transport=_transport(handler))
    ans = await GeminiAnswerer(c).answer(_plan(), [_hit()])
    # Falls back to template answerer, which still lists the place.
    assert "Halal Place" in ans.answer
    await c.aclose()
