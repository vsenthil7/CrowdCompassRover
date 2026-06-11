"""Integration tests for the now load-bearing modules.

These verify the modules are actually wired into the request path, not just unit-correct:
events flow into the outbox, the outbox relays to webhooks, tenancy partitions data, the
bulkhead fronts search, and the SLO records failures as well as successes.
"""
from __future__ import annotations

import pytest

from app.concurrency.bulkhead import Bulkhead, BulkheadFullError
from app.core.config import AppMode, Settings
from app.core.providers import build_components
from app.events.bus import EventBus, RouteRequested, SearchPerformed
from app.events.outbox_bridge import OutboxBridge, WebhookOutboxSink
from app.outbox.store import Outbox
from app.slo.tracker import SloTracker
from app.tenancy.context import TenantContext
from app.tenancy.scoped_store import TenantScopedStore
from app.webhooks.dispatcher import WebhookDispatcher, WebhookRegistry, WebhookSubscription


# --- outbox bridge ---


async def test_bridge_enqueues_published_events():
    bus = EventBus()
    outbox = Outbox()
    bridge = OutboxBridge(bus, outbox, tenant="acme")
    bridge.bridge("search.performed")

    await bus.publish(SearchPerformed(query="halal", language="en", result_count=3))
    pending = outbox.pending()
    assert len(pending) == 1
    assert pending[0].topic == "search.performed"
    assert pending[0].payload["query"] == "halal"
    assert pending[0].metadata["tenant"] == "acme"


async def test_bridge_ignores_unbridged_events():
    bus = EventBus()
    outbox = Outbox()
    OutboxBridge(bus, outbox).bridge("search.performed")
    await bus.publish(RouteRequested(destination="X", cheapest_mode="walk"))
    assert outbox.size == 0


async def test_webhook_outbox_sink_delivers():
    registry = WebhookRegistry()
    registry.register(
        WebhookSubscription(
            id="s1", tenant="default", url="https://hook", secret="secret12",
            events={"search.performed"},
        )
    )
    sent = {"n": 0}

    async def sender(url, headers, body):
        sent["n"] += 1
        return 200

    sink = WebhookOutboxSink(WebhookDispatcher(registry, sender))
    outbox = Outbox()
    outbox.enqueue("search.performed", {"q": "halal"}, tenant="default")
    result = await outbox.relay(sink)
    assert result["delivered"] == 1
    assert sent["n"] == 1


async def test_webhook_outbox_sink_failure_keeps_pending():
    registry = WebhookRegistry()
    registry.register(
        WebhookSubscription(
            id="s1", tenant="default", url="https://hook", secret="secret12",
            events={"search.performed"},
        )
    )

    async def failing_sender(url, headers, body):
        return 500  # non-2xx -> not delivered

    sink = WebhookOutboxSink(WebhookDispatcher(registry, failing_sender))
    outbox = Outbox()
    outbox.enqueue("search.performed", {}, tenant="default", max_attempts=3)
    result = await outbox.relay(sink)
    assert result["failed"] == 1
    assert len(outbox.pending()) == 1  # retried later


async def test_webhook_outbox_sink_no_subscribers_is_success():
    sink = WebhookOutboxSink(WebhookDispatcher(WebhookRegistry(), lambda u, h, b: None))  # type: ignore[arg-type]
    outbox = Outbox()
    outbox.enqueue("search.performed", {}, tenant="default")
    result = await outbox.relay(sink)
    # No subscribers -> nothing to deliver -> message considered delivered (drained).
    assert result["delivered"] == 1


# --- tenant scoped store ---


async def test_tenant_store_partitions():
    store: TenantScopedStore[str] = TenantScopedStore()
    acme = TenantContext("acme")
    globex = TenantContext("globex")
    await store.put(acme, "k", "acme-value")
    await store.put(globex, "k", "globex-value")
    assert await store.get(acme, "k") == "acme-value"
    assert await store.get(globex, "k") == "globex-value"
    # No cross-tenant visibility.
    assert await store.count(acme) == 1
    assert await store.list_values(globex) == ["globex-value"]


async def test_tenant_store_isolation_on_missing():
    store: TenantScopedStore[str] = TenantScopedStore()
    acme = TenantContext("acme")
    assert await store.get(acme, "missing") is None
    assert await store.delete(acme, "missing") is False
    await store.put(acme, "k", "v")
    assert await store.delete(acme, "k") is True
    assert await store.list_keys(acme) == []


async def test_tenant_store_tenant_ids():
    store: TenantScopedStore[int] = TenantScopedStore()
    await store.put(TenantContext("a"), "k", 1)
    await store.put(TenantContext("b"), "k", 2)
    assert set(await store.tenant_ids()) == {"a", "b"}


# --- bulkhead actually fronts search ---


async def test_search_runs_through_bulkhead():
    comp = build_components(Settings(app_mode=AppMode.MOCK))
    # The agent holds the same bulkhead instance exposed on Components.
    assert comp.agent._bulkhead is comp.bulkhead
    await comp.agent.search("halal food", None, 3)
    # Bulkhead returned to idle after the call.
    assert comp.bulkhead.stats().active == 0


async def test_orchestrator_records_slo_failure_on_pipeline_error():
    from app.agent.orchestrator import RoverAgent

    class _BoomPipeline:
        async def run(self, plan):
            raise RuntimeError("downstream down")

        async def list_indices(self):
            return []

    class _Planner:
        async def plan(self, q, loc, k):
            from app.models.domain import QueryPlan, SearchFilters

            return QueryPlan(
                original_query=q, detected_language="en", normalized_query=q,
                semantic_text=q, filters=SearchFilters(), top_k=k,
            )

    slo = SloTracker()
    agent = RoverAgent(_Planner(), _BoomPipeline(), answerer=None, slo=slo)
    with pytest.raises(RuntimeError):
        await agent.search("x", None, 3)
    report = slo.report("search")
    assert report.failures == 1
    assert report.meeting_slo is False
    # chat path records its own failure too
    with pytest.raises(RuntimeError):
        await agent.chat("x", None)
    assert slo.report("chat").failures == 1


async def test_bulkhead_rejection_surfaces_from_search():
    # A zero-capacity bulkhead forces rejection to prove it's actually in the path.
    from app.agent.orchestrator import RoverAgent

    class _Pipeline:
        async def run(self, plan):
            return []

        async def list_indices(self):
            return []

    class _Planner:
        async def plan(self, q, loc, k):
            from app.models.domain import QueryPlan, SearchFilters

            return QueryPlan(
                original_query=q, detected_language="en", normalized_query=q,
                semantic_text=q, filters=SearchFilters(), top_k=k,
            )

    import asyncio

    bh = Bulkhead("search", max_concurrent=1, max_queue=0)
    agent = RoverAgent(_Planner(), _Pipeline(), answerer=None, bulkhead=bh)

    # Saturate the single slot with a blocker run directly on the bulkhead.
    release = asyncio.Event()

    async def blocker():
        await release.wait()

    holder = asyncio.create_task(bh.run(blocker))
    await asyncio.sleep(0.01)
    with pytest.raises(BulkheadFullError):
        await agent.search("x", None, 3)
    release.set()
    await holder


# --- factory exposes wired collaborators ---


def test_factory_wires_outbox_sink_and_bridge():
    comp = build_components(Settings(app_mode=AppMode.MOCK))
    assert comp.outbox_sink is not None
    # The bus has handlers for the bridged events (bridge subscribed them).
    assert comp.event_bus.handler_count("search.performed") >= 1


async def test_search_publishes_into_outbox_via_factory():
    comp = build_components(Settings(app_mode=AppMode.MOCK))
    await comp.agent.search("halal food open now", None, 3)
    # The bridge enqueued the search.performed event durably.
    assert comp.outbox.size >= 1
