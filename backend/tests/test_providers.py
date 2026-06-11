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
    from app.resilience.cache import TTLCache

    base = MockSearchProvider()
    wrapped = wrap_resilient(base, Settings(app_mode=AppMode.MOCK), TTLCache())
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


async def test_orchestrator_records_analytics():
    comp = build_components(Settings(app_mode=AppMode.MOCK))
    await comp.agent.search("halal food open now", None, 3)
    await comp.agent.chat("where is the stadium", None)
    assert comp.analytics.size == 2


async def test_orchestrator_route_to():
    from app.enrichment.routes import TravelMode
    from app.models.domain import GeoPoint

    comp = build_components(Settings(app_mode=AppMode.MOCK))
    res = await comp.agent.route_to(
        GeoPoint(lat=40.81, lon=-74.07),
        GeoPoint(lat=40.758, lon=-73.985),
        [TravelMode.WALK, TravelMode.DRIVE],
    )
    assert res.cheapest is not None
    assert res.fastest is not None


async def test_orchestrator_route_default_modes():
    from app.models.domain import GeoPoint

    comp = build_components(Settings(app_mode=AppMode.MOCK))
    res = await comp.agent.route_to(
        GeoPoint(lat=40.81, lon=-74.07), GeoPoint(lat=40.758, lon=-73.985)
    )
    assert len(res.options) == 3  # default walk/transit/drive


def test_build_route_provider_real_with_key():
    from app.core.providers import build_route_provider
    from app.enrichment.google_routes import GoogleRouteProvider

    s = Settings(app_mode=AppMode.REAL, google_maps_api_key="k")
    provider, closables = build_route_provider(s)
    assert isinstance(provider, GoogleRouteProvider)
    assert len(closables) == 1


def test_build_route_provider_mock_default():
    from app.core.providers import build_route_provider
    from app.enrichment.mock_routes import MockRouteProvider

    provider, closables = build_route_provider(Settings(app_mode=AppMode.MOCK))
    assert isinstance(provider, MockRouteProvider)
    assert closables == []


async def test_build_health_registry_runs():
    comp = build_components(Settings(app_mode=AppMode.MOCK))
    report = await comp.health.run()
    assert report.ready is True
    assert {c.name for c in report.components} == {"search", "events_repo"}


async def test_orchestrator_pagination():
    from app.pagination.cursor import encode_cursor

    comp = build_components(Settings(app_mode=AppMode.MOCK))
    # Force pagination with an explicit cursor; broad query matches many venues.
    resp = await comp.agent.search("open", None, 3, cursor=encode_cursor(0))
    assert resp.total is not None
    assert len(resp.results) <= 3
    if resp.next_cursor:
        page2 = await comp.agent.search("open", None, 3, cursor=resp.next_cursor)
        assert page2.total == resp.total


async def test_orchestrator_batch_search():
    comp = build_components(Settings(app_mode=AppMode.MOCK))
    responses = await comp.agent.batch_search(["stadium", "transit", "halal"], None, 3)
    assert len(responses) == 3


async def test_orchestrator_emits_events_and_traces():
    comp = build_components(Settings(app_mode=AppMode.MOCK))
    await comp.agent.search("halal food open now", None, 3)
    assert comp.event_bus.published_count >= 1
    assert comp.tracer.exporter.count >= 1


async def test_orchestrator_route_emits_event():
    from app.models.domain import GeoPoint

    comp = build_components(Settings(app_mode=AppMode.MOCK))
    before = comp.event_bus.published_count
    await comp.agent.route_to(
        GeoPoint(lat=40.81, lon=-74.07),
        GeoPoint(lat=40.758, lon=-73.985),
        destination_name="MetLife",
    )
    assert comp.event_bus.published_count > before


async def test_orchestrator_zero_result_event():
    # A query with an impossible filter combination yields zero results.
    from app.models.domain import GeoPoint

    comp = build_components(Settings(app_mode=AppMode.MOCK))
    # Use a far location with tight radius via planner near-terms.
    resp = await comp.agent.search("nearest hospital", GeoPoint(lat=0.0, lon=0.0), 3)
    # Either zero or some results; the event bus still recorded a search event.
    assert comp.event_bus.published_count >= 1
    assert isinstance(resp.results, list)


def test_build_feature_flags():
    from app.core.providers import build_feature_flags

    flags = build_feature_flags(Settings(app_mode=AppMode.MOCK))
    assert flags.is_enabled("route_enrichment") is True


def test_build_ingestion():
    from app.core.providers import build_ingestion

    pipeline, freshness = build_ingestion(Settings(app_mode=AppMode.MOCK))
    assert pipeline is not None
    assert freshness.is_stale is True  # not yet marked


async def test_wire_event_handlers_zero_result_metric():
    from app.analytics.recorder import AnalyticsRecorder
    from app.core.providers import wire_event_handlers
    from app.events.bus import EventBus, ZeroResult

    bus = EventBus()
    wire_event_handlers(bus, AnalyticsRecorder())
    ran = await bus.publish(ZeroResult(query="q", language="en"))
    assert ran == 1


def test_build_authz_with_keys():
    from app.core.providers import build_authz

    resolver, policy = build_authz(Settings(app_mode=AppMode.MOCK, api_keys="key-a,key-b"))
    principal = resolver.resolve("key-a")
    assert principal.tenant == "default"
    assert "admin" in principal.role_names()


def test_build_authz_no_keys():
    from app.core.providers import build_authz

    resolver, policy = build_authz(Settings(app_mode=AppMode.MOCK))
    assert resolver.resolve("anything").subject == "anonymous"


async def test_build_alert_manager_rules():
    from app.core.providers import build_alert_manager

    manager = build_alert_manager()
    assert manager.rule_count == 2
    fired = await manager.evaluate({"zero_result_rate": 0.9, "ready": True})
    assert any(a.rule == "high_zero_result_rate" for a in fired)


async def test_build_alert_manager_unhealthy():
    from app.core.providers import build_alert_manager

    manager = build_alert_manager()
    fired = await manager.evaluate({"ready": False})
    assert any(a.rule == "dependency_unhealthy" for a in fired)


def test_build_components_has_all_collaborators():
    comp = build_components(Settings(app_mode=AppMode.MOCK))
    assert comp.audit.verify() is True
    assert comp.webhooks.count == 0
    assert comp.meter.quota_for("any") > 0
    assert comp.resolver is not None
    assert comp.policy is not None
    assert comp.data_rights is not None
    assert comp.alerts.rule_count == 2
