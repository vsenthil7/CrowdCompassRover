"""Integration tests for the FastAPI routes and dependency lifecycle."""
from __future__ import annotations

import httpx
import pytest
from asgi_lifespan import LifespanManager

from app.api import deps
from app.main import create_app


@pytest.fixture
async def client():
    # Reset module-level component cache for isolation.
    deps._components = None
    app = create_app()
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    deps._components = None


async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mode"] == "mock"


async def test_indices(client):
    r = await client.get("/api/indices")
    assert r.status_code == 200
    assert "cc-city-events" in r.json()["indices"]


async def test_search_endpoint(client):
    r = await client.post(
        "/api/search",
        json={"query": "halal food open now", "user_location": {"lat": 40.81, "lon": -74.07}, "top_k": 3},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["plan"]["filters"]["halal"] is True
    assert len(body["results"]) <= 3


async def test_search_validation_error(client):
    r = await client.post("/api/search", json={"query": ""})
    assert r.status_code == 422


async def test_chat_endpoint(client):
    r = await client.post("/api/chat", json={"query": "where is the stadium"})
    assert r.status_code == 200
    body = r.json()
    assert body["language"] == "en"
    assert "answer" in body


async def test_chat_stream_endpoint(client):
    r = await client.post("/api/chat/stream", json={"query": "halal food open now"})
    assert r.status_code == 200
    text = r.text
    assert "event: language" in text
    assert "event: token" in text
    assert "event: done" in text


async def test_ready_endpoint(client):
    r = await client.get("/api/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert body["state"] == "healthy"


async def test_analytics_endpoint(client):
    await client.post("/api/search", json={"query": "halal food open now"})
    r = await client.get("/api/analytics")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert "by_language" in body
    assert "top_queries" in body


async def test_routes_endpoint(client):
    r = await client.post(
        "/api/routes",
        json={
            "origin": {"lat": 40.81, "lon": -74.07},
            "destination": {"lat": 40.758, "lon": -73.985},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["cheapest"] is not None
    assert body["fastest"] is not None
    assert len(body["options"]) == 3


async def test_routes_endpoint_explicit_modes(client):
    r = await client.post(
        "/api/routes",
        json={
            "origin": {"lat": 40.81, "lon": -74.07},
            "destination": {"lat": 40.758, "lon": -73.985},
            "modes": ["walk", "drive"],
        },
    )
    assert r.status_code == 200
    assert len(r.json()["options"]) == 2


async def test_metrics_endpoint_present(client):
    await client.get("/api/health")
    r = await client.get("/api/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text


async def test_search_pagination(client):
    from app.pagination.cursor import encode_cursor

    r = await client.post(
        "/api/search",
        json={"query": "open", "top_k": 3, "cursor": encode_cursor(0)},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] is not None
    assert len(body["results"]) <= 3


async def test_batch_search_endpoint(client):
    r = await client.post(
        "/api/search/batch",
        json={"queries": ["stadium", "transit"], "top_k": 3},
    )
    assert r.status_code == 200
    assert len(r.json()["responses"]) == 2


async def test_saved_search_crud(client):
    create = await client.post(
        "/api/saved-searches",
        json={"owner": "owner1", "query": "halal food", "label": "My spots"},
    )
    assert create.status_code == 200
    sid = create.json()["id"]
    got = await client.get(f"/api/saved-searches/owner1/{sid}")
    assert got.status_code == 200
    assert got.json()["query"] == "halal food"
    deleted = await client.delete(f"/api/saved-searches/owner1/{sid}")
    assert deleted.status_code == 200


async def test_saved_search_not_found(client):
    r = await client.get("/api/saved-searches/owner1/missing")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")


async def test_saved_search_delete_missing(client):
    r = await client.delete("/api/saved-searches/owner1/missing")
    assert r.status_code == 404


async def test_flags_endpoint(client):
    r = await client.get("/api/flags")
    assert r.status_code == 200
    assert "route_enrichment" in r.json()["flags"]


async def test_traces_endpoint(client):
    await client.post("/api/search", json={"query": "halal food"})
    r = await client.get("/api/traces")
    assert r.status_code == 200
    spans = r.json()["spans"]
    assert any(s["name"] == "search" for s in spans)


async def test_admin_status_endpoint(client):
    r = await client.get("/api/admin/status")
    assert r.status_code == 200
    assert "events" in r.json()


async def test_admin_flush_cache_endpoint(client):
    r = await client.post("/api/admin/cache/flush")
    assert r.status_code == 200
    assert r.json()["flushed"] is True


async def test_admin_reindex_endpoint(client):
    r = await client.post("/api/admin/reindex")
    assert r.status_code == 200
    assert r.json()["indexed"] >= 1


async def test_get_agent_lazy_init():
    # When components not initialized, get_agent should build them on demand.
    deps._components = None
    agent = deps.get_agent()
    assert agent is not None
    deps._components = None


async def test_shutdown_when_uninitialized_is_safe():
    deps._components = None
    await deps.shutdown_components()  # should not raise


async def test_shutdown_closes_closables():
    closed = {"v": False}

    class _C:
        async def aclose(self):
            closed["v"] = True

    from app.core.providers import Components
    from app.conversation.session import SessionStore
    from app.analytics.recorder import AnalyticsRecorder
    from app.health.checks import HealthRegistry
    from app.persistence.memory import InMemoryEventRepository
    from app.tracing.tracer import Tracer
    from app.events.bus import EventBus
    from app.flags.feature_flags import FeatureFlags
    from app.persistence.saved_search import SavedSearchService
    from app.admin.service import AdminService
    from app.ingestion.pipeline import FreshnessTracker, IngestionPipeline
    from app.resilience.cache import TTLCache

    repo = InMemoryEventRepository()
    flags = FeatureFlags()
    admin = AdminService(
        cache=TTLCache(),
        events=repo,
        pipeline=IngestionPipeline([]),
        freshness=FreshnessTracker(),
        flags=flags,
    )
    deps._components = Components(
        agent=object(),
        sessions=SessionStore(),
        analytics=AnalyticsRecorder(),
        events=repo,
        health=HealthRegistry(),
        tracer=Tracer(),
        event_bus=EventBus(),
        flags=flags,
        saved_searches=SavedSearchService(),
        admin=admin,
        closables=[_C(), object()],
    )
    await deps.shutdown_components()
    assert closed["v"] is True
    assert deps._components is None
