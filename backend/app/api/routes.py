"""HTTP routes for CrowdCompass Rover."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Response
from sse_starlette.sse import EventSourceResponse

from app.agent.orchestrator import RoverAgent
from app.analytics.recorder import AnalyticsRecorder
from app.api.deps import (
    get_agent,
    get_analytics,
    get_health_registry,
    get_sessions,
)
from app.conversation.session import SessionStore
from app.core.config import Settings, get_settings
from app.enrichment.routes import TravelMode
from app.health.checks import HealthRegistry
from app.models.domain import (
    ChatAnswer,
    ChatRequest,
    RouteRequest,
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
    """Run a hybrid multilingual search."""
    return await agent.search(req.query, req.user_location, req.top_k, req.session_id)


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
