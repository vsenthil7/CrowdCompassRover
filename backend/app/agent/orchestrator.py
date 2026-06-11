"""Agent orchestrator: plan -> contextualise -> search pipeline -> ground.

Coordinates planning, multi-turn context resolution, the ranking-enhanced search pipeline,
grounded answering, analytics capture, and optional route enrichment. Sessions, analytics,
and routing are all optional collaborators injected by the factory.
"""
from __future__ import annotations

import time

from app.agent.answerer import Answerer
from app.agent.planner import Planner
from app.analytics.recorder import AnalyticsRecorder
from app.conversation.context import apply_context
from app.conversation.session import SessionStore
from app.enrichment.routes import RouteProvider, RouteResult, TravelMode
from app.models.domain import (
    ChatAnswer,
    GeoPoint,
    QueryPlan,
    SearchResponse,
)
from app.services.search_pipeline import SearchPipeline


class RoverAgent:
    """Top-level agent coordinating planning, retrieval, grounding and enrichment."""

    def __init__(
        self,
        planner: Planner,
        pipeline: SearchPipeline,
        answerer: Answerer,
        sessions: SessionStore | None = None,
        analytics: AnalyticsRecorder | None = None,
        routes: RouteProvider | None = None,
        *,
        clock=time.perf_counter,
    ) -> None:
        self._planner = planner
        self._pipeline = pipeline
        self._answerer = answerer
        self._sessions = sessions
        self._analytics = analytics
        self._routes = routes
        self._clock = clock

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

    def _record(self, plan: QueryPlan, count: int, elapsed_ms: float) -> None:
        if self._analytics is not None:
            self._analytics.record(
                plan.original_query,
                plan.detected_language,
                count,
                category=plan.filters.category.value if plan.filters.category else None,
                city=plan.filters.city,
                duration_ms=elapsed_ms,
            )

    async def search(
        self,
        query: str,
        user_location: GeoPoint | None,
        top_k: int,
        session_id: str | None = None,
    ) -> SearchResponse:
        """Plan and run the search pipeline, returning ranked results plus the plan."""
        start = self._clock()
        plan = await self._plan_with_context(query, user_location, top_k, session_id)
        results = await self._pipeline.run(plan)
        self._record(plan, len(results), (self._clock() - start) * 1000)
        return SearchResponse(plan=plan, results=results)

    async def chat(
        self,
        query: str,
        user_location: GeoPoint | None,
        top_k: int = 5,
        session_id: str | None = None,
    ) -> ChatAnswer:
        """Plan, search and produce a grounded, cited answer."""
        start = self._clock()
        plan = await self._plan_with_context(query, user_location, top_k, session_id)
        results = await self._pipeline.run(plan)
        self._record(plan, len(results), (self._clock() - start) * 1000)
        return await self._answerer.answer(plan, results)

    async def route_to(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        modes: list[TravelMode] | None = None,
    ) -> RouteResult:
        """Compute route options to a destination (the 'cheapest route' use case)."""
        if self._routes is None:  # pragma: no cover - factory always injects a provider
            raise RuntimeError("no route provider configured")
        chosen = modes or [TravelMode.WALK, TravelMode.TRANSIT, TravelMode.DRIVE]
        return await self._routes.routes(origin, destination, chosen)

    async def list_indices(self) -> list[str]:
        """Expose the pipeline's index listing."""
        return await self._pipeline.list_indices()
