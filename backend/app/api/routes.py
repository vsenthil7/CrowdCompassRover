"""HTTP routes for CrowdCompass Rover."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request, Response
from sse_starlette.sse import EventSourceResponse

from app.agent.orchestrator import RoverAgent
from app.analytics.recorder import AnalyticsRecorder
from app.api.deps import (
    get_admin,
    get_agent,
    get_analytics,
    get_audit,
    get_bulkhead,
    get_data_rights,
    get_flags,
    get_health_registry,
    get_idempotency,
    get_meter,
    get_outbox,
    get_outbox_sink,
    get_retention,
    get_saved_searches,
    get_sessions,
    get_slo,
    get_tenants,
    get_tracer,
    get_versions,
    get_webhooks,
)
from app.idempotency.store import KeyState
from app.conversation.session import SessionStore
from app.core.config import Settings, get_settings
from app.enrichment.routes import TravelMode
from app.errors.exceptions import NotFoundError
from app.health.checks import HealthRegistry
from app.models.domain import (
    BatchSearchRequest,
    ChatAnswer,
    ChatRequest,
    RouteRequest,
    SavedSearchRequest,
    SearchRequest,
    SearchResponse,
    WebhookRequest,
)
from app.observability.metrics import get_metrics

router = APIRouter()


@router.get("/health")
async def health(
    settings: Settings = Depends(get_settings),
    sessions: SessionStore = Depends(get_sessions),
) -> dict:
    """Liveness + active-mode + lightweight runtime stats."""
    return {
        "status": "ok",
        "mode": settings.app_mode.value,
        "sessions_active": sessions.active_count,
        "features": {
            "reranking": settings.enable_reranking,
            "query_expansion": settings.enable_query_expansion,
            "spell_correction": settings.enable_spell_correction,
        },
    }


@router.get("/ready")
async def ready(
    registry: HealthRegistry = Depends(get_health_registry),
) -> Response:
    """Readiness probe: runs dependency health checks."""
    report = await registry.run()
    status = 200 if report.ready else 503
    return Response(
        content=json.dumps(report.to_dict()),
        media_type="application/json",
        status_code=status,
    )


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus text-format metrics."""
    return Response(content=get_metrics().render(), media_type="text/plain; version=0.0.4")


@router.get("/analytics")
async def analytics(
    recorder: AnalyticsRecorder = Depends(get_analytics),
) -> dict:
    """Aggregated query analytics snapshot."""
    snap = recorder.snapshot()
    return {
        "total": snap.total,
        "zero_result": snap.zero_result,
        "zero_result_rate": round(snap.zero_result_rate, 4),
        "by_language": snap.by_language,
        "by_category": snap.by_category,
        "top_queries": snap.top_queries,
    }


@router.get("/indices")
async def indices(agent: RoverAgent = Depends(get_agent)) -> dict:
    """List searchable indices via the active search provider."""
    names = await agent.list_indices()
    return {"indices": names}


@router.post("/search", response_model=SearchResponse)
async def search(
    req: SearchRequest, agent: RoverAgent = Depends(get_agent)
) -> SearchResponse:
    """Run a hybrid multilingual search with optional cursor pagination."""
    return await agent.search(
        req.query, req.user_location, req.top_k, req.session_id, req.cursor
    )


@router.post("/chat", response_model=ChatAnswer)
async def chat(
    req: ChatRequest, agent: RoverAgent = Depends(get_agent)
) -> ChatAnswer:
    """Return a grounded, cited answer (non-streaming)."""
    return await agent.chat(req.query, req.user_location, session_id=req.session_id)


@router.post("/routes")
async def routes(
    req: RouteRequest, agent: RoverAgent = Depends(get_agent)
) -> dict:
    """Compute route options to a destination ('cheapest route to the stadium')."""
    modes = None
    if req.modes is not None:
        modes = [TravelMode(m) for m in req.modes]
    result = await agent.route_to(req.origin, req.destination, modes)
    return {
        "options": [o.model_dump() for o in result.options],
        "cheapest": result.cheapest.model_dump() if result.cheapest else None,
        "fastest": result.fastest.model_dump() if result.fastest else None,
    }


@router.post("/search/batch")
async def search_batch(
    req: BatchSearchRequest, agent: RoverAgent = Depends(get_agent)
) -> dict:
    """Run several queries in one call."""
    responses = await agent.batch_search(req.queries, req.user_location, req.top_k)
    return {"responses": [r.model_dump() for r in responses]}


@router.post("/saved-searches")
async def create_saved_search(
    req: SavedSearchRequest, service=Depends(get_saved_searches)
) -> dict:
    """Persist a saved search for an owner."""
    saved = await service.save(req.owner, req.query, req.label, req.tags)
    return {
        "id": saved.id,
        "owner": saved.owner,
        "query": saved.query,
        "label": saved.label,
        "tags": saved.tags,
    }


@router.get("/saved-searches/{owner}/{search_id}")
async def get_saved_search(owner: str, search_id: str, service=Depends(get_saved_searches)) -> dict:
    """Fetch a saved search; 404 problem if missing."""
    saved = await service.get(owner, search_id)
    if saved is None:
        raise NotFoundError("saved search not found")
    return {"id": saved.id, "query": saved.query, "label": saved.label, "tags": saved.tags}


@router.delete("/saved-searches/{owner}/{search_id}")
async def delete_saved_search(owner: str, search_id: str, service=Depends(get_saved_searches)) -> dict:
    """Delete a saved search."""
    deleted = await service.delete(owner, search_id)
    if not deleted:
        raise NotFoundError("saved search not found")
    return {"deleted": True}


@router.get("/flags")
async def flags(registry=Depends(get_flags)) -> dict:
    """Return evaluated feature flags."""
    return {"flags": registry.all_flags()}


@router.get("/traces")
async def traces(tracer=Depends(get_tracer)) -> dict:
    """Return recently recorded spans (most recent first)."""
    spans = tracer.exporter.finished()[-50:]
    return {
        "spans": [
            {
                "trace_id": s.trace_id,
                "span_id": s.span_id,
                "parent_id": s.parent_id,
                "name": s.name,
                "duration_ms": round(s.duration_ms, 3),
                "status": s.status,
                "attributes": s.attributes,
            }
            for s in reversed(spans)
        ]
    }


@router.get("/admin/status")
async def admin_status(admin=Depends(get_admin)) -> dict:
    """Operational status summary."""
    return await admin.status()


@router.post("/admin/cache/flush")
async def admin_flush_cache(admin=Depends(get_admin)) -> dict:
    """Flush the search cache."""
    return await admin.flush_cache()


@router.post("/admin/reindex")
async def admin_reindex(
    request: Request,
    admin=Depends(get_admin),
    idempotency=Depends(get_idempotency),
) -> dict:
    """Trigger a reindex from ingestion sources.

    Honours an optional ``Idempotency-Key`` header so a retried reindex returns the prior
    result instead of running twice.
    """
    key = request.headers.get("Idempotency-Key")
    if key:
        state, cached = await idempotency.begin(key)
        if state != KeyState.NEW:
            return {**cached, "idempotent_replay": True}
    result = await admin.reindex()
    payload = {"indexed": result.indexed, "healthy": result.healthy}
    if key:
        await idempotency.complete(key, payload)
    return payload


@router.get("/audit")
async def audit_log(audit=Depends(get_audit)) -> dict:
    """Return recent audit entries and chain-integrity status."""
    entries = audit.entries()[-100:]
    return {
        "verified": audit.verify(),
        "count": audit.size,
        "entries": [
            {
                "seq": e.seq,
                "actor": e.actor,
                "tenant": e.tenant,
                "action": e.action,
                "resource": e.resource,
                "outcome": e.outcome,
                "ts": e.ts,
            }
            for e in entries
        ],
    }


@router.post("/webhooks")
async def create_webhook(
    req: WebhookRequest, registry=Depends(get_webhooks), audit=Depends(get_audit)
) -> dict:
    """Register a webhook subscription."""
    import uuid

    from app.webhooks.dispatcher import WebhookSubscription

    sub = WebhookSubscription(
        id=uuid.uuid4().hex[:12],
        tenant=req.tenant,
        url=req.url,
        secret=req.secret,
        events=set(req.events),
    )
    registry.register(sub)
    audit.record(req.tenant, req.tenant, "webhook.create", sub.id, "success")
    return {"id": sub.id, "events": sorted(sub.events)}


@router.delete("/webhooks/{sub_id}")
async def delete_webhook(sub_id: str, registry=Depends(get_webhooks)) -> dict:
    """Remove a webhook subscription."""
    if not registry.remove(sub_id):
        raise NotFoundError("webhook not found")
    return {"deleted": True}


@router.get("/usage/{tenant}")
async def usage(tenant: str, meter=Depends(get_meter), tenants=Depends(get_tenants)) -> dict:
    """Return current-period usage and remaining quota for a validated tenant."""
    ctx = tenants.resolve(principal_tenant=None, header_tenant=tenant)
    tenant_id = ctx.tenant_id
    current = meter.current(tenant_id)
    return {
        "tenant": tenant_id,
        "period": current.period,
        "count": current.count,
        "by_action": current.by_action,
        "remaining": meter.remaining(tenant_id),
        "quota": meter.quota_for(tenant_id),
    }


@router.get("/gdpr/export/{subject}")
async def gdpr_export(subject: str, service=Depends(get_data_rights)) -> dict:
    """Export all data held about a subject."""
    doc = await service.export(subject)
    return doc.to_dict()


@router.delete("/gdpr/{subject}")
async def gdpr_purge(subject: str, service=Depends(get_data_rights), audit=Depends(get_audit)) -> dict:
    """Purge a subject's data."""
    result = await service.purge(subject)
    audit.record(subject, "default", "gdpr.purge", subject, "success")
    return {
        "subject": result.subject,
        "sessions_removed": result.sessions_removed,
        "saved_searches_removed": result.saved_searches_removed,
    }


@router.get("/slo")
async def slo_report(tracker=Depends(get_slo)) -> dict:
    """Per-service SLO status and error budgets."""
    out = []
    for service in tracker.services():
        r = tracker.report(service)
        out.append(
            {
                "service": r.service,
                "target": r.target,
                "total": r.total,
                "success_ratio": round(r.success_ratio, 4),
                "meeting_slo": r.meeting_slo,
                "budget_remaining": round(r.budget_remaining, 4),
            }
        )
    return {"services": out}


@router.get("/version")
async def version_info(registry=Depends(get_versions)) -> dict:
    """Supported API versions and the current one."""
    return {"current": registry.current, "supported": registry.supported_names()}


@router.post("/admin/outbox/relay")
async def outbox_relay(outbox=Depends(get_outbox), sink=Depends(get_outbox_sink)) -> dict:
    """Drain pending outbox messages to webhook subscribers (relay step)."""
    return await outbox.relay(sink)


@router.get("/admin/outbox")
async def outbox_stats(outbox=Depends(get_outbox)) -> dict:
    """Outbox message counts by state, with any dead letters."""
    return {
        "stats": outbox.stats(),
        "dead_letters": [
            {"id": m.id, "topic": m.topic, "attempts": m.attempts, "error": m.last_error}
            for m in outbox.dead_letters()
        ],
    }


@router.get("/admin/bulkhead")
async def bulkhead_stats(bulkhead=Depends(get_bulkhead)) -> dict:
    """Concurrency bulkhead utilisation."""
    s = bulkhead.stats()
    return {
        "name": s.name,
        "max_concurrent": s.max_concurrent,
        "active": s.active,
        "queued": s.queued,
        "rejected": s.rejected,
    }


@router.post("/admin/retention/sweep")
async def retention_sweep(sweeper=Depends(get_retention), audit=Depends(get_audit)) -> dict:
    """Apply retention policies, returning per-source removal counts."""
    results = sweeper.sweep()
    audit.record("system", "default", "retention.sweep", "all", "success")
    return {"swept": [{"name": r.name, "removed": r.removed} for r in results]}


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest, agent: RoverAgent = Depends(get_agent)
) -> EventSourceResponse:
    """Stream a grounded answer as Server-Sent Events."""
    answer = await agent.chat(req.query, req.user_location, session_id=req.session_id)

    async def event_gen():
        yield {"event": "language", "data": answer.language}
        for line in answer.answer.split("\n"):
            yield {"event": "token", "data": line}
        yield {
            "event": "done",
            "data": json.dumps(
                {
                    "citations": [c.model_dump() for c in answer.citations],
                    "results": [r.model_dump() for r in answer.results],
                }
            ),
        }

    return EventSourceResponse(event_gen())
