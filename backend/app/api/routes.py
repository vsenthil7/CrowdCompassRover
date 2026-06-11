"""HTTP routes for CrowdCompass Rover."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Response
from sse_starlette.sse import EventSourceResponse

from app.agent.orchestrator import RoverAgent
from app.analytics.recorder import AnalyticsRecorder
from app.api.deps import (
    get_admin,
    get_agent,
    get_analytics,
    get_flags,
    get_health_registry,
    get_saved_searches,
    get_sessions,
    get_tracer,
)
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
async def admin_reindex(admin=Depends(get_admin)) -> dict:
    """Trigger a reindex from ingestion sources."""
    result = await admin.reindex()
    return {"indexed": result.indexed, "healthy": result.healthy}


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
