"""Agent orchestrator: plan -> contextualise -> search pipeline -> ground.

Coordinates planning, multi-turn context resolution, the ranking-enhanced search pipeline,
and grounded answering. Sessions are optional: when a ``session_id`` is supplied, prior
turn context is carried forward and the new turn is recorded.
"""
from __future__ import annotations

from app.agent.answerer import Answerer
from app.agent.planner import Planner
from app.conversation.context import apply_context
from app.conversation.session import SessionStore
from app.models.domain import (
    ChatAnswer,
    GeoPoint,
    QueryPlan,
    SearchResponse,
)
from app.services.search_pipeline import SearchPipeline


class RoverAgent:
    """Top-level agent coordinating planning, retrieval and grounding."""

    def __init__(
        self,
        planner: Planner,
        pipeline: SearchPipeline,
        answerer: Answerer,
        sessions: SessionStore | None = None,
    ) -> None:
        self._planner = planner
        self._pipeline = pipeline
        self._answerer = answerer
        self._sessions = sessions

    async def _plan_with_context(
        self, query: str, user_location: GeoPoint | None, top_k: int, session_id: str | None
    ) -> QueryPlan:
        """Produce a plan, enriching it with prior session context when applicable."""
        plan = await self._planner.plan(query, user_location, top_k)
        if self._sessions is not None and session_id:
            session = self._sessions.get(session_id)
            prior = session.last_plan if session else None
            plan = apply_context(plan, prior)
            self._sessions.record(session_id, query, plan)
        return plan

    async def search(
        self,
        query: str,
        user_location: GeoPoint | None,
        top_k: int,
        session_id: str | None = None,
    ) -> SearchResponse:
        """Plan and run the search pipeline, returning ranked results plus the plan."""
        plan = await self._plan_with_context(query, user_location, top_k, session_id)
        results = await self._pipeline.run(plan)
        return SearchResponse(plan=plan, results=results)

    async def chat(
        self,
        query: str,
        user_location: GeoPoint | None,
        top_k: int = 5,
        session_id: str | None = None,
    ) -> ChatAnswer:
        """Plan, search and produce a grounded, cited answer."""
        plan = await self._plan_with_context(query, user_location, top_k, session_id)
        results = await self._pipeline.run(plan)
        return await self._answerer.answer(plan, results)

    async def list_indices(self) -> list[str]:
        """Expose the pipeline's index listing."""
        return await self._pipeline.list_indices()
