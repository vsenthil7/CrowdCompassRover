"""Tests for the provider factory and orchestrator wiring."""
from __future__ import annotations

from app.agent.gemini_planner import GeminiAnswerer, GeminiPlanner
from app.agent.answerer import MockAnswerer
from app.agent.planner import MockPlanner
from app.core.config import AppMode, Settings
from app.core.providers import (
    build_base_search_provider,
    build_components,
    build_pipeline,
    build_planner_and_answerer,
    wrap_resilient,
)
from app.models.domain import GeoPoint
from app.services.elastic_search import ElasticSearchProvider
from app.services.mock_search import MockSearchProvider
from app.services.resilient_search import ResilientSearchProvider
from app.services.search_pipeline import SearchPipeline


def test_build_base_search_provider_mock():
    provider, closables = build_base_search_provider(Settings(app_mode=AppMode.MOCK))
    assert isinstance(provider, MockSearchProvider)
    assert closables == []


def test_build_base_search_provider_real_with_creds():
    s = Settings(
        app_mode=AppMode.REAL,
        elastic_mcp_url="http://mcp",
        elastic_mcp_api_key="key",
    )
    provider, closables = build_base_search_provider(s)
    assert isinstance(provider, ElasticSearchProvider)
    assert len(closables) == 1


def test_build_base_search_provider_real_without_creds_falls_back():
    provider, _ = build_base_search_provider(Settings(app_mode=AppMode.REAL))
    assert isinstance(provider, MockSearchProvider)


def test_wrap_resilient():
    base = MockSearchProvider()
    wrapped = wrap_resilient(base, Settings(app_mode=AppMode.MOCK))
    assert isinstance(wrapped, ResilientSearchProvider)


def test_build_pipeline_with_and_without_features():
    base = MockSearchProvider()
    p_full = build_pipeline(base, Settings(app_mode=AppMode.MOCK))
    assert isinstance(p_full, SearchPipeline)
    p_off = build_pipeline(
        base,
        Settings(
            app_mode=AppMode.MOCK,
            enable_spell_correction=False,
            enable_query_expansion=False,
            enable_reranking=False,
        ),
    )
    assert isinstance(p_off, SearchPipeline)


def test_build_planner_answerer_mock():
    planner, answerer, closables = build_planner_and_answerer(Settings(app_mode=AppMode.MOCK))
    assert isinstance(planner, MockPlanner)
    assert isinstance(answerer, MockAnswerer)
    assert closables == []


def test_build_planner_answerer_real_with_key():
    s = Settings(app_mode=AppMode.REAL, gemini_api_key="k")
    planner, answerer, closables = build_planner_and_answerer(s)
    assert isinstance(planner, GeminiPlanner)
    assert isinstance(answerer, GeminiAnswerer)
    assert len(closables) == 1


def test_build_planner_answerer_real_without_key_falls_back():
    planner, _, _ = build_planner_and_answerer(Settings(app_mode=AppMode.REAL))
    assert isinstance(planner, MockPlanner)


def test_build_components_mock():
    comp = build_components(Settings(app_mode=AppMode.MOCK))
    assert comp.agent is not None
    assert comp.sessions is not None
    assert comp.closables == []


async def test_orchestrator_search_and_chat():
    comp = build_components(Settings(app_mode=AppMode.MOCK))
    agent = comp.agent
    resp = await agent.search("halal food open now", GeoPoint(lat=40.81, lon=-74.07), 3)
    assert resp.plan.filters.halal is True
    assert len(resp.results) <= 3
    ans = await agent.chat("where is the stadium", None)
    assert ans.answer
    indices = await agent.list_indices()
    assert "cc-city-events" in indices


async def test_orchestrator_multiturn_session():
    comp = build_components(Settings(app_mode=AppMode.MOCK))
    agent = comp.agent
    sid = "s1"
    r1 = await agent.search("halal food in mexico city", None, 5, session_id=sid)
    assert r1.plan.filters.city == "Mexico City"
    r2 = await agent.search("what about open ones", None, 5, session_id=sid)
    assert r2.plan.filters.city == "Mexico City"
    assert r2.plan.filters.open_now is True


async def test_orchestrator_chat_with_session():
    comp = build_components(Settings(app_mode=AppMode.MOCK))
    ans = await comp.agent.chat("halal food", None, session_id="s2")
    assert ans.answer
    assert comp.sessions.active_count == 1
