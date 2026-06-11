"""Agent orchestrator: plan -> search -> ground.

Coordinates the three pluggable components (planner, search provider, answerer). The same
orchestrator is used in every mode; only the injected components differ.
"""
from __future__ import annotations

from app.agent.answerer import Answerer
from app.agent.planner import Planner
from app.models.domain import (
    ChatAnswer,
    GeoPoint,
    SearchResponse,
)
from app.services.search_provider import SearchProvider


class RoverAgent:
    """Top-level agent coordinating planning, retrieval and grounding."""

    def __init__(
        self,
        planner: Planner,
        search: SearchProvider,
        answerer: Answerer,
    ) -> None:
        self._planner = planner
        self._search = search
        self._answerer = answerer

    async def search(
        self, query: str, user_location: GeoPoint | None, top_k: int
    ) -> SearchResponse:
        """Plan and run a search, returning ranked results plus the plan."""
        plan = await self._planner.plan(query, user_location, top_k)
        results = await self._search.search(plan)
        return SearchResponse(plan=plan, results=results)

    async def chat(
        self, query: str, user_location: GeoPoint | None, top_k: int = 5
    ) -> ChatAnswer:
        """Plan, search and produce a grounded, cited answer."""
        plan = await self._planner.plan(query, user_location, top_k)
        results = await self._search.search(plan)
        return await self._answerer.answer(plan, results)

    async def list_indices(self) -> list[str]:
        """Expose the search provider's index listing."""
        return await self._search.list_indices()
