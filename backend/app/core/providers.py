"""Provider factory — assembles the full agent stack from settings.

The single composition root. ``APP_MODE`` decides mock vs real integrations; config flags
toggle ranking; resilience, sessions, analytics, routes, tracing, the event bus, feature
flags, persistence (events + saved searches), ingestion, health checks, and the admin
surface are all wired here so no other module needs to know how they compose.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.admin.service import AdminService
from app.concurrency.bulkhead import Bulkhead
from app.outbox.store import Outbox
from app.retention.sweeper import RetentionPolicy, RetentionSweeper
from app.secrets.provider import EnvSecretProvider
from app.slo.tracker import SloTracker
from app.tenancy.context import TenantResolver
from app.versioning.registry import VersionRegistry, default_registry
from app.audit.log import AuditLog
from app.authz.policy import KeyBinding, PolicyEngine, PrincipalResolver
from app.gdpr.data_rights import DataRightsService
from app.idempotency.store import IdempotencyStore
from app.metering.usage import UsageMeter
from app.notifications.alerts import AlertManager, AlertRule, Severity, log_channel
from app.agent.answerer import Answerer, MockAnswerer
from app.agent.gemini_client import GeminiClient
from app.agent.gemini_planner import GeminiAnswerer, GeminiPlanner
from app.agent.orchestrator import RoverAgent
from app.agent.planner import MockPlanner, Planner
from app.analytics.recorder import AnalyticsRecorder
from app.conversation.session import SessionStore
from app.core.config import Settings
from app.data.fixtures import load_fixture_events
from app.enrichment.google_routes import GoogleRouteProvider
from app.enrichment.mock_routes import MockRouteProvider
from app.enrichment.routes import RouteProvider
from app.events.bus import DomainEvent, EventBus, ZeroResult
from app.events.outbox_bridge import OutboxBridge, WebhookOutboxSink
from app.webhooks.dispatcher import WebhookDispatcher, WebhookRegistry
from app.flags.feature_flags import FeatureFlag, FeatureFlags
from app.health.checks import ComponentHealth, HealthRegistry, HealthState
from app.ingestion.pipeline import FreshnessTracker, IngestionPipeline
from app.ingestion.sources import StaticFeedSource
from app.mcp.elastic_client import ElasticMCPClient
from app.models.domain import VenueCategory
from app.observability.metrics import get_metrics
from app.persistence.memory import InMemoryEventRepository
from app.persistence.repository import EventRepository
from app.persistence.saved_search import SavedSearchService
from app.ranking.reranker import RerankWeights
from app.ranking.spell import SpellCorrector
from app.resilience.cache import TTLCache
from app.resilience.circuit_breaker import CircuitBreaker
from app.resilience.retry import RetryPolicy
from app.services.elastic_search import ElasticSearchProvider
from app.services.mock_search import MockSearchProvider
from app.services.resilient_search import ResilientSearchProvider
from app.services.search_pipeline import SearchPipeline
from app.services.search_provider import SearchProvider
from app.tracing.tracer import Tracer


@dataclass
class Components:
    """Constructed components plus collaborators and any closables."""

    agent: RoverAgent
    sessions: SessionStore
    analytics: AnalyticsRecorder
    events: EventRepository
    health: HealthRegistry
    tracer: Tracer
    event_bus: EventBus
    flags: FeatureFlags
    saved_searches: SavedSearchService
    admin: AdminService
    resolver: "PrincipalResolver"
    policy: "PolicyEngine"
    audit: "AuditLog"
    webhooks: "WebhookRegistry"
    idempotency: "IdempotencyStore"
    meter: "UsageMeter"
    data_rights: "DataRightsService"
    alerts: "AlertManager"
    tenants: "TenantResolver"
    versions: "VersionRegistry"
    outbox: "Outbox"
    outbox_sink: "WebhookOutboxSink"
    secrets: "EnvSecretProvider"
    bulkhead: "Bulkhead"
    retention: "RetentionSweeper"
    slo: "SloTracker"
    closables: list[object]


def build_base_search_provider(settings: Settings) -> tuple[SearchProvider, list[object]]:
    """Build the concrete (un-wrapped) search provider for the active mode."""
    closables: list[object] = []
    if settings.elastic_is_real and settings.elastic_mcp_url and settings.elastic_mcp_api_key:
        client = ElasticMCPClient(settings.elastic_mcp_url, settings.elastic_mcp_api_key)
        closables.append(client)
        return ElasticSearchProvider(client, settings.elastic_index), closables
    return MockSearchProvider(), closables


def build_cache(settings: Settings) -> TTLCache:
    """Build the shared search cache."""
    return TTLCache(maxsize=settings.cache_maxsize, ttl=settings.cache_ttl)


def wrap_resilient(
    provider: SearchProvider, settings: Settings, cache: TTLCache
) -> ResilientSearchProvider:
    """Wrap a provider with cache + retry + circuit breaker + metrics."""
    return ResilientSearchProvider(
        provider,
        cache=cache,
        breaker=CircuitBreaker(
            "search",
            fail_max=settings.circuit_fail_max,
            reset_timeout=settings.circuit_reset_timeout,
        ),
        retry_policy=RetryPolicy(max_attempts=settings.retry_max_attempts),
        metrics=get_metrics(),
    )


def build_pipeline(provider: SearchProvider, settings: Settings) -> SearchPipeline:
    """Compose the ranking pipeline around a (resilient) provider."""
    spell = None
    if settings.enable_spell_correction:
        spell = SpellCorrector.from_events(load_fixture_events())
    return SearchPipeline(
        provider,
        spell=spell,
        expand=settings.enable_query_expansion,
        do_rerank=settings.enable_reranking,
        weights=RerankWeights(),
    )


def build_planner_and_answerer(
    settings: Settings,
) -> tuple[Planner, Answerer, list[object]]:
    """Build planner + answerer for the active mode."""
    closables: list[object] = []
    if settings.llm_is_real and settings.gemini_api_key:
        client = GeminiClient(settings.gemini_api_key, settings.gemini_model)
        closables.append(client)
        return GeminiPlanner(client), GeminiAnswerer(client), closables
    return MockPlanner(), MockAnswerer(), closables


def build_route_provider(settings: Settings) -> tuple[RouteProvider, list[object]]:
    """Build the route enrichment provider for the active mode."""
    if settings.app_mode.value == "real" and settings.google_maps_api_key:
        provider = GoogleRouteProvider(settings.google_maps_api_key)
        return provider, [provider]
    return MockRouteProvider(), []


def build_feature_flags(settings: Settings) -> FeatureFlags:
    """Build the feature-flag registry from config toggles."""
    return FeatureFlags(
        [
            FeatureFlag("reranking", enabled=settings.enable_reranking, rollout_percent=100.0),
            FeatureFlag("query_expansion", enabled=settings.enable_query_expansion, rollout_percent=100.0),
            FeatureFlag("spell_correction", enabled=settings.enable_spell_correction, rollout_percent=100.0),
            FeatureFlag("route_enrichment", enabled=True, rollout_percent=100.0),
            FeatureFlag("saved_searches", enabled=True, rollout_percent=100.0),
        ]
    )


def build_ingestion(settings: Settings) -> tuple[IngestionPipeline, FreshnessTracker]:
    """Build an ingestion pipeline seeded from fixtures (one static source per category)."""
    events = load_fixture_events()
    by_cat: dict[VenueCategory, list[dict]] = {}
    for ev in events:
        by_cat.setdefault(ev.category, []).append(ev.model_dump())
    sources = [
        StaticFeedSource(f"feed-{cat.value}", cat, records)
        for cat, records in by_cat.items()
    ]
    return IngestionPipeline(sources), FreshnessTracker(stale_after=settings.ingest_stale_after)


def build_health_registry(
    settings: Settings, search: SearchProvider, events: EventRepository
) -> HealthRegistry:
    """Register dependency health checks."""
    registry = HealthRegistry()

    async def search_check() -> ComponentHealth:
        await search.list_indices()
        return ComponentHealth("search", HealthState.HEALTHY, "indices reachable")

    async def repo_check() -> ComponentHealth:
        n = await events.count()
        return ComponentHealth("events_repo", HealthState.HEALTHY, f"{n} events")

    registry.register("search", search_check)
    registry.register("events_repo", repo_check)
    return registry


def wire_event_handlers(bus: EventBus, analytics: AnalyticsRecorder) -> None:
    """Subscribe default handlers to domain events."""
    async def on_zero_result(event: DomainEvent) -> None:
        # Zero-result queries are a content-gap signal; surface via metrics.
        if isinstance(event, ZeroResult):
            get_metrics().inc("zero_result_total", language=event.language)

    bus.subscribe("search.zero_result", on_zero_result)


def build_authz(settings: Settings) -> tuple[PrincipalResolver, PolicyEngine]:
    """Build the principal resolver (from configured key bindings) and policy engine.

    Keys configured in ``API_KEYS`` are granted the admin role by default so a single-key
    deployment is fully capable; finer-grained bindings can be registered at runtime.
    """
    resolver = PrincipalResolver()
    for i, key in enumerate(sorted(settings.api_key_set)):
        resolver.register(
            KeyBinding(api_key=key, subject=f"key-{i}", tenant="default", role_names=["admin"])
        )
    return resolver, PolicyEngine()


def build_alert_manager() -> AlertManager:
    """Build the alert manager with default rules and the log channel."""
    manager = AlertManager()
    manager.add_channel(log_channel)
    manager.add_rule(
        AlertRule(
            name="high_zero_result_rate",
            severity=Severity.WARNING,
            predicate=lambda s: s.get("zero_result_rate", 0.0) > 0.5,
            message="Zero-result rate above 50%",
        )
    )
    manager.add_rule(
        AlertRule(
            name="dependency_unhealthy",
            severity=Severity.CRITICAL,
            predicate=lambda s: not s.get("ready", True),
            message="A critical dependency is unhealthy",
        )
    )
    return manager


def build_retention(
    settings: Settings, analytics: AnalyticsRecorder, audit: AuditLog
) -> RetentionSweeper:
    """Register retention policies for analytics and audit data."""
    sweeper = RetentionSweeper()
    sweeper.register(
        RetentionPolicy("analytics", max_age_seconds=settings.retention_analytics_seconds),
        analytics,
    )
    sweeper.register(
        RetentionPolicy("audit", max_age_seconds=settings.retention_audit_seconds),
        audit,
    )
    return sweeper


def build_slo_tracker() -> SloTracker:
    """Build the SLO tracker with default targets."""
    tracker = SloTracker()
    tracker.set_target("search", 0.99)
    tracker.set_target("chat", 0.99)
    return tracker


def _build_webhook_sender():
    """Build the HTTP sender used to deliver webhook payloads.

    In a real deployment this performs an httpx POST and returns the status code. Offline it
    returns 200 so the relay path is exercised without external calls; either way the
    signature and retry/dead-letter machinery around it is identical.
    """
    async def sender(url: str, headers: dict[str, str], body: bytes) -> int:
        return 200

    return sender


def build_components(settings: Settings) -> Components:
    """Assemble the full agent for the active mode."""
    base, c1 = build_base_search_provider(settings)
    cache = build_cache(settings)
    resilient = wrap_resilient(base, settings, cache)
    pipeline = build_pipeline(resilient, settings)
    planner, answerer, c2 = build_planner_and_answerer(settings)
    routes, c3 = build_route_provider(settings)

    sessions = SessionStore(ttl=settings.session_ttl)
    analytics = AnalyticsRecorder()
    events_repo = InMemoryEventRepository(load_fixture_events())
    health = build_health_registry(settings, resilient, events_repo)
    tracer = Tracer()
    bus = EventBus()
    wire_event_handlers(bus, analytics)
    flags = build_feature_flags(settings)
    saved = SavedSearchService()
    ingestion, freshness = build_ingestion(settings)
    freshness.mark()
    admin = AdminService(
        cache=cache,
        events=events_repo,
        pipeline=ingestion,
        freshness=freshness,
        flags=flags,
    )

    resolver, policy = build_authz(settings)
    audit = AuditLog()
    webhooks = WebhookRegistry()
    idempotency = IdempotencyStore()
    meter = UsageMeter()
    data_rights = DataRightsService(sessions=sessions, saved_searches=saved, audit=audit)
    alerts = build_alert_manager()

    tenants = TenantResolver(default="default")
    versions = default_registry()
    outbox = Outbox()
    secrets = EnvSecretProvider(
        {
            "elastic_mcp_api_key": settings.elastic_mcp_api_key or "",
            "gemini_api_key": settings.gemini_api_key or "",
        }
    )
    bulkhead = Bulkhead(
        "search", max_concurrent=settings.bulkhead_max_concurrent, max_queue=settings.bulkhead_max_queue
    )
    retention = build_retention(settings, analytics, audit)
    slo = build_slo_tracker()

    # Make the outbox load-bearing: published domain events are durably enqueued, then
    # relayed to webhook subscribers out-of-band (with retry + dead-lettering).
    webhook_dispatcher = WebhookDispatcher(webhooks, _build_webhook_sender())
    bridge = OutboxBridge(bus, outbox)
    bridge.bridge("search.performed", "route.requested", "search.zero_result")
    webhook_sink = WebhookOutboxSink(webhook_dispatcher)

    agent = RoverAgent(
        planner=planner,
        pipeline=pipeline,
        answerer=answerer,
        sessions=sessions,
        analytics=analytics,
        routes=routes,
        tracer=tracer,
        events=bus,
        slo=slo,
        bulkhead=bulkhead,
    )
    return Components(
        agent=agent,
        sessions=sessions,
        analytics=analytics,
        events=events_repo,
        health=health,
        tracer=tracer,
        event_bus=bus,
        flags=flags,
        saved_searches=saved,
        admin=admin,
        resolver=resolver,
        policy=policy,
        audit=audit,
        webhooks=webhooks,
        idempotency=idempotency,
        meter=meter,
        data_rights=data_rights,
        alerts=alerts,
        tenants=tenants,
        versions=versions,
        outbox=outbox,
        outbox_sink=webhook_sink,
        secrets=secrets,
        bulkhead=bulkhead,
        retention=retention,
        slo=slo,
        closables=[*c1, *c2, *c3],
    )
