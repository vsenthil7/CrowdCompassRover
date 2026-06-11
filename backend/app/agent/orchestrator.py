"""Agent orchestrator: plan -> contextualise -> search pipeline -> ground.

Coordinates planning, multi-turn context, the ranking-enhanced search pipeline, grounded
answering, analytics, route enrichment, distributed tracing, domain-event publication,
input sanitisation, and cursor pagination. Every collaborator is optional and injected by
the factory, so the orchestrator stays a thin coordinator.
"""
from __future__ import annotations

import time

from app.agent.answerer import Answerer
from app.agent.planner import Planner
from app.analytics.recorder import AnalyticsRecorder
from app.concurrency.bulkhead import Bulkhead
from app.conversation.context import apply_context
from app.conversation.session import SessionStore
from app.enrichment.routes import RouteProvider, RouteResult, TravelMode
from app.events.bus import EventBus, RouteRequested, SearchPerformed, ZeroResult
from app.models.domain import (
    ChatAnswer,
    GeoPoint,
    QueryPlan,
    ScoredEvent,
    SearchResponse,
)
from app.pagination.cursor import Page, paginate
from app.security.sanitize import sanitize_query
from app.services.search_pipeline import SearchPipeline
from app.slo.tracker import SloTracker
from app.tracing.tracer import Tracer


class RoverAgent:
    """Top-level agent coordinating the full request lifecycle."""

    def __init__(
        self,
        planner: Planner,
        pipeline: SearchPipeline,
        answerer: Answerer,
        sessions: SessionStore | None = None,
        analytics: AnalyticsRecorder | None = None,
        routes: RouteProvider | None = None,
        tracer: Tracer | None = None,
        events: EventBus | None = None,
        slo: SloTracker | None = None,
        bulkhead: "Bulkhead | None" = None,
        *,
        clock=time.perf_counter,
    ) -> None:
        self._planner = planner
        self._pipeline = pipeline
        self._answerer = answerer
        self._sessions = sessions
        self._analytics = analytics
        self._routes = routes
        self._tracer = tracer or Tracer()
        self._events = events
        self._slo = slo
        self._bulkhead = bulkhead
        self._clock = clock

    async def _run_pipeline(self, plan: QueryPlan):
        """Run the search pipeline, behind the bulkhead when one is configured."""
        if self._bulkhead is not None:
            return await self._bulkhead.run(lambda: self._pipeline.run(plan))
        return await self._pipeline.run(plan)

    async def _plan_with_context(
        self, query: str, user_location: GeoPoint | None, top_k: int, session_id: str | None
    ) -> QueryPlan:
        """Sanitise input, plan, and enrich with prior session context."""
        with self._tracer.start("plan") as span:
            cleaned = sanitize_query(query)
            span.set_attribute("sanitize.actions", ",".join(cleaned.actions))
            span.set_attribute("sanitize.flagged", cleaned.flagged)
            plan = await self._planner.plan(cleaned.value, user_location, top_k)
            if self._sessions is not None and session_id:
                session = self._sessions.get(session_id)
                prior = session.last_plan if session else None
                plan = apply_context(plan, prior)
                self._sessions.record(session_id, cleaned.value, plan)
            span.set_attribute("language", plan.detected_language)
            return plan

    async def _emit(self, plan: QueryPlan, count: int, elapsed_ms: float) -> None:
        if self._analytics is not None:
            self._analytics.record(
                plan.original_query,
                plan.detected_language,
                count,
                category=plan.filters.category.value if plan.filters.category else None,
                city=plan.filters.city,
                duration_ms=elapsed_ms,
            )
        if self._events is not None:
            await self._events.publish(
                SearchPerformed(
                    query=plan.original_query,
                    language=plan.detected_language,
                    result_count=count,
                )
            )
            if count == 0:
                await self._events.publish(
                    ZeroResult(query=plan.original_query, language=plan.detected_language)
                )

    async def search(
        self,
        query: str,
        user_location: GeoPoint | None,
        top_k: int,
        session_id: str | None = None,
        cursor: str | None = None,
    ) -> SearchResponse:
        """Plan and run the search pipeline, with optional cursor pagination."""
        with self._tracer.start("search") as span:
            start = self._clock()
            paginating = cursor is not None
            # When paginating, retrieve a larger candidate window so pages are stable.
            effective_k = max(top_k * 5, top_k) if paginating else top_k
            plan = await self._plan_with_context(
                query, user_location, effective_k, session_id
            )
            with self._tracer.start("retrieve"):
                try:
                    results = await self._run_pipeline(plan)
                except Exception:
                    if self._slo is not None:
                        self._slo.record("search", False)
                    raise
            span.set_attribute("results", len(results))
            await self._emit(plan, len(results), (self._clock() - start) * 1000)
            if self._slo is not None:
                self._slo.record("search", True)

            next_cursor = None
            total = None
            if paginating or len(results) > top_k:
                page: Page[ScoredEvent] = paginate(results, cursor=cursor, limit=top_k)
                results = page.items
                next_cursor = page.next_cursor
                total = page.total
            return SearchResponse(
                plan=plan, results=results, next_cursor=next_cursor, total=total
            )

    async def batch_search(
        self, queries: list[str], user_location: GeoPoint | None, top_k: int
    ) -> list[SearchResponse]:
        """Run several queries, returning one response each."""
        with self._tracer.start("batch_search") as span:
            span.set_attribute("queries", len(queries))
            return [await self.search(q, user_location, top_k) for q in queries]

    async def chat(
        self,
        query: str,
        user_location: GeoPoint | None,
        top_k: int = 5,
        session_id: str | None = None,
    ) -> ChatAnswer:
        """Plan, search and produce a grounded, cited answer."""
        with self._tracer.start("chat"):
            start = self._clock()
            plan = await self._plan_with_context(query, user_location, top_k, session_id)
            try:
                results = await self._run_pipeline(plan)
            except Exception:
                if self._slo is not None:
                    self._slo.record("chat", False)
                raise
            await self._emit(plan, len(results), (self._clock() - start) * 1000)
            if self._slo is not None:
                self._slo.record("chat", True)
            with self._tracer.start("ground"):
                return await self._answerer.answer(plan, results)

    async def route_to(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        modes: list[TravelMode] | None = None,
        destination_name: str = "",
    ) -> RouteResult:
        """Compute route options to a destination (the 'cheapest route' use case)."""
        if self._routes is None:  # pragma: no cover - factory always injects a provider
            raise RuntimeError("no route provider configured")
        with self._tracer.start("route"):
            chosen = modes or [TravelMode.WALK, TravelMode.TRANSIT, TravelMode.DRIVE]
            result = await self._routes.routes(origin, destination, chosen)
            if self._events is not None:
                cheapest = result.cheapest
                await self._events.publish(
                    RouteRequested(
                        destination=destination_name,
                        cheapest_mode=cheapest.mode.value if cheapest else None,
                    )
                )
            return result

    async def list_indices(self) -> list[str]:
        """Expose the pipeline's index listing."""
        return await self._pipeline.list_indices()
