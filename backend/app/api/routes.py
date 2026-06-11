"""HTTP routes for CrowdCompass Rover."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.agent.orchestrator import RoverAgent
from app.api.deps import get_agent
from app.core.config import Settings, get_settings
from app.models.domain import (
    ChatAnswer,
    ChatRequest,
    SearchRequest,
    SearchResponse,
)

router = APIRouter()


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict:
    """Liveness + active-mode report."""
    return {"status": "ok", "mode": settings.app_mode.value}


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
    return await agent.search(req.query, req.user_location, req.top_k)


@router.post("/chat", response_model=ChatAnswer)
async def chat(
    req: ChatRequest, agent: RoverAgent = Depends(get_agent)
) -> ChatAnswer:
    """Return a grounded, cited answer (non-streaming)."""
    return await agent.chat(req.query, req.user_location)


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest, agent: RoverAgent = Depends(get_agent)
) -> EventSourceResponse:
    """Stream a grounded answer as Server-Sent Events.

    Emits a ``plan`` event, then ``token`` events for the answer text, then a final
    ``done`` event carrying citations and results.
    """
    answer = await agent.chat(req.query, req.user_location)

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
