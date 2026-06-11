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


# An admin API key for exercising permission-gated routes. Any key in API_KEYS is
# granted the admin role by build_authz(), so this header satisfies every
# policy.require() check on elevated routes.
ADMIN_KEY = "test-admin-key"


@pytest.fixture
async def admin_client(monkeypatch):
    """A client whose requests carry an admin API key (X-API-Key header)."""
    from app.core import config as config_module

    monkeypatch.setenv("API_KEYS", ADMIN_KEY)
    config_module.get_settings.cache_clear()
    deps._components = None
    app = create_app()
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test", headers={"X-API-Key": ADMIN_KEY}
        ) as c:
            yield c
    deps._components = None
    config_module.get_settings.cache_clear()


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


async def test_analytics_endpoint(admin_client):
    await admin_client.post("/api/search", json={"query": "halal food open now"})
    r = await admin_client.get("/api/analytics")
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


async def test_traces_endpoint(admin_client):
    await admin_client.post("/api/search", json={"query": "halal food"})
    r = await admin_client.get("/api/traces")
    assert r.status_code == 200
    spans = r.json()["spans"]
    assert any(s["name"] == "search" for s in spans)


async def test_admin_status_endpoint(admin_client):
    r = await admin_client.get("/api/admin/status")
    assert r.status_code == 200
    assert "events" in r.json()


async def test_admin_flush_cache_endpoint(admin_client):
    r = await admin_client.post("/api/admin/cache/flush")
    assert r.status_code == 200
    assert r.json()["flushed"] is True


async def test_admin_reindex_endpoint(admin_client):
    r = await admin_client.post("/api/admin/reindex")
    assert r.status_code == 200
    assert r.json()["indexed"] >= 1


async def test_admin_reindex_idempotent_replay(admin_client):
    first = await admin_client.post("/api/admin/reindex", headers={"Idempotency-Key": "abc123"})
    assert first.status_code == 200
    assert "idempotent_replay" not in first.json()
    second = await admin_client.post("/api/admin/reindex", headers={"Idempotency-Key": "abc123"})
    assert second.status_code == 200
    assert second.json()["idempotent_replay"] is True
    assert second.json()["indexed"] == first.json()["indexed"]


async def test_audit_endpoint(client):
    r = await client.get("/api/audit")
    assert r.status_code == 200
    body = r.json()
    assert body["verified"] is True
    assert "entries" in body


async def test_webhook_create_and_delete(admin_client):
    create = await admin_client.post(
        "/api/webhooks",
        json={
            "tenant": "acme",
            "url": "https://example.com/hook",
            "secret": "supersecret",
            "events": ["search.performed"],
        },
    )
    assert create.status_code == 200
    wid = create.json()["id"]
    deleted = await admin_client.delete(f"/api/webhooks/{wid}")
    assert deleted.status_code == 200


async def test_webhook_delete_missing(admin_client):
    r = await admin_client.delete("/api/webhooks/missing")
    assert r.status_code == 404


async def test_usage_endpoint(client):
    r = await client.get("/api/usage/acme")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant"] == "acme"
    assert "remaining" in body
    assert "quota" in body


async def test_gdpr_export_endpoint(admin_client):
    # Create some data first.
    await admin_client.post(
        "/api/saved-searches",
        json={"owner": "alice", "query": "halal", "label": "h"},
    )
    r = await admin_client.get("/api/gdpr/export/alice")
    assert r.status_code == 200
    body = r.json()
    assert body["subject"] == "alice"
    assert len(body["saved_searches"]) >= 1


async def test_gdpr_purge_endpoint(admin_client):
    await admin_client.post(
        "/api/saved-searches",
        json={"owner": "bob", "query": "halal", "label": "h"},
    )
    r = await admin_client.request("DELETE", "/api/gdpr/bob")
    assert r.status_code == 200
    assert r.json()["saved_searches_removed"] >= 1


async def test_slo_endpoint(client):
    await client.post("/api/search", json={"query": "halal food"})
    r = await client.get("/api/slo")
    assert r.status_code == 200
    services = r.json()["services"]
    assert any(s["service"] == "search" for s in services)


async def test_version_endpoint(client):
    r = await client.get("/api/version")
    assert r.status_code == 200
    body = r.json()
    assert body["current"] == "v1"
    assert "v1" in body["supported"]


async def test_outbox_stats_endpoint(client):
    r = await client.get("/api/admin/outbox")
    assert r.status_code == 200
    assert "stats" in r.json()
    assert "dead_letters" in r.json()


async def test_outbox_relay_delivers_to_subscriber(admin_client):
    # Register a subscriber for search.performed, run a search (enqueues via bridge),
    # then relay — exercises the factory-built webhook sender end to end.
    create = await admin_client.post(
        "/api/webhooks",
        json={
            "tenant": "default",
            "url": "https://example.com/hook",
            "secret": "supersecret",
            "events": ["search.performed"],
        },
    )
    assert create.status_code == 200
    await admin_client.post("/api/search", json={"query": "halal food open now"})
    r = await admin_client.post("/api/admin/outbox/relay")
    assert r.status_code == 200
    assert r.json()["delivered"] >= 1


async def test_bulkhead_stats_endpoint(client):
    r = await client.get("/api/admin/bulkhead")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "search"
    assert body["max_concurrent"] >= 1


async def test_retention_sweep_endpoint(admin_client):
    r = await admin_client.post("/api/admin/retention/sweep")
    assert r.status_code == 200
    swept = r.json()["swept"]
    names = {s["name"] for s in swept}
    assert {"analytics", "audit"} <= names


async def test_availability_endpoint_default_now(client):
    r = await client.get("/api/availability/nyc-penn-station")
    assert r.status_code == 200
    body = r.json()
    assert body["venue_id"] == "nyc-penn-station"
    # Penn Station is transit → always open.
    assert body["is_open"] is True
    assert body["open_state"] == "open"


async def test_availability_endpoint_at_time(client):
    # A restaurant at 04:00 UTC should be closed (hours 08:00–23:30).
    r = await client.get("/api/availability/nyc-halal-cart-8th?at=2026-06-02T04:00:00Z")
    assert r.status_code == 200
    assert r.json()["is_open"] is False


async def test_availability_endpoint_bad_time(client):
    r = await client.get("/api/availability/nyc-penn-station?at=not-a-time")
    assert r.status_code == 422


async def test_report_live_signal_then_reflected(client):
    # Report a 'packed' signal and confirm the resolved availability reflects it.
    r = await client.post(
        "/api/availability/signals",
        json={"venue_id": "nyc-penn-station", "crowd": "packed", "wait_minutes": 30},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["crowd"] == "packed"
    assert body["wait_minutes"] == 30


async def test_report_live_signal_temporary_closure(client):
    r = await client.post(
        "/api/availability/signals",
        json={"venue_id": "nyc-fan-zone-central", "temporarily_closed": True, "note": "weather"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["temporarily_closed"] is True
    assert body["effectively_open"] is False


async def test_report_live_signal_bad_crowd(client):
    r = await client.post(
        "/api/availability/signals",
        json={"venue_id": "nyc-penn-station", "crowd": "bananas"},
    )
    assert r.status_code == 422


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

    async def _noop_sender(url, headers, body):
        return 200

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
    from app.authz.policy import PolicyEngine, PrincipalResolver
    from app.audit.log import AuditLog
    from app.webhooks.dispatcher import WebhookRegistry
    from app.idempotency.store import IdempotencyStore
    from app.metering.usage import UsageMeter
    from app.gdpr.data_rights import DataRightsService
    from app.notifications.alerts import AlertManager

    from app.notifications.alerts import AlertManager
    from app.tenancy.context import TenantResolver
    from app.versioning.registry import default_registry
    from app.outbox.store import Outbox
    from app.events.outbox_bridge import WebhookOutboxSink
    from app.webhooks.dispatcher import WebhookDispatcher
    from app.secrets.provider import EnvSecretProvider
    from app.concurrency.bulkhead import Bulkhead
    from app.retention.sweeper import RetentionSweeper
    from app.slo.tracker import SloTracker
    from app.availability.service import AvailabilityService

    repo = InMemoryEventRepository()
    flags = FeatureFlags()
    sessions = SessionStore()
    saved = SavedSearchService()
    audit = AuditLog()
    admin = AdminService(
        cache=TTLCache(),
        events=repo,
        pipeline=IngestionPipeline([]),
        freshness=FreshnessTracker(),
        flags=flags,
    )
    deps._components = Components(
        agent=object(),
        sessions=sessions,
        analytics=AnalyticsRecorder(),
        events=repo,
        health=HealthRegistry(),
        tracer=Tracer(),
        event_bus=EventBus(),
        flags=flags,
        saved_searches=saved,
        admin=admin,
        resolver=PrincipalResolver(),
        policy=PolicyEngine(),
        audit=audit,
        webhooks=WebhookRegistry(),
        idempotency=IdempotencyStore(),
        meter=UsageMeter(),
        data_rights=DataRightsService(sessions=sessions, saved_searches=saved, audit=audit),
        alerts=AlertManager(),
        tenants=TenantResolver(),
        versions=default_registry(),
        outbox=Outbox(),
        outbox_sink=WebhookOutboxSink(WebhookDispatcher(WebhookRegistry(), _noop_sender)),
        secrets=EnvSecretProvider(),
        bulkhead=Bulkhead("test"),
        retention=RetentionSweeper(),
        slo=SloTracker(),
        availability=AvailabilityService(),
        closables=[_C(), object()],
    )
    await deps.shutdown_components()
    assert closed["v"] is True
    assert deps._components is None
