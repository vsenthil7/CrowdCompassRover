"""Gemini-backed planner and answerer (REAL mode).

These satisfy the same Planner / Answerer protocols as the mock implementations. They
build prompts, call Gemini, and map the structured output back into domain objects. A
mock-planner fallback guarantees a valid plan even if the model returns partial data.
"""
from __future__ import annotations

from app.agent.answerer import MockAnswerer
from app.agent.gemini_client import GeminiClient
from app.agent.planner import MockPlanner
from app.models.domain import (
    Citation,
    ChatAnswer,
    GeoPoint,
    QueryPlan,
    ScoredEvent,
    SearchFilters,
    VenueCategory,
)

_PLAN_SYSTEM = (
    "You are a multilingual query planner for a World Cup host-city search agent. "
    "Given a user question in any language, return STRICT JSON with keys: "
    "detected_language (ISO code), normalized_query (English), semantic_text (English), "
    "filters (object with optional city, category, open_now, halal, vegetarian, "
    "wheelchair_accessible). category must be one of: stadium, restaurant, transit, "
    "currency_exchange, fan_zone, hospital, hotel, pop_up_vendor, info_kiosk. "
    "Return only JSON, no prose, no code fences."
)

_ANSWER_SYSTEM = (
    "You are a concise multilingual concierge. Answer in the user's language using ONLY "
    "the provided results. Cite each place by name. Keep it short and practical."
)


class GeminiPlanner:
    """LLM-backed planner with a deterministic fallback."""

    def __init__(self, client: GeminiClient) -> None:
        self._client = client
        self._fallback = MockPlanner()

    async def plan(
        self, query: str, user_location: GeoPoint | None, top_k: int
    ) -> QueryPlan:
        """Plan via Gemini, falling back to the mock planner on any failure."""
        try:
            data = await self._client.generate_json(_PLAN_SYSTEM, query)
        except Exception:  # noqa: BLE001 - resilience: degrade to deterministic plan
            return await self._fallback.plan(query, user_location, top_k)

        raw_filters = data.get("filters", {}) or {}
        category = raw_filters.get("category")
        filters = SearchFilters(
            city=raw_filters.get("city"),
            category=VenueCategory(category) if category in VenueCategory._value2member_map_ else None,
            open_now=raw_filters.get("open_now"),
            halal=raw_filters.get("halal"),
            vegetarian=raw_filters.get("vegetarian"),
            wheelchair_accessible=raw_filters.get("wheelchair_accessible"),
        )
        if user_location is not None and raw_filters.get("near"):
            filters.near = user_location
            filters.max_distance_km = float(raw_filters.get("max_distance_km", 25.0))

        return QueryPlan(
            original_query=query,
            detected_language=data.get("detected_language", "en"),
            normalized_query=data.get("normalized_query", query),
            semantic_text=data.get("semantic_text", data.get("normalized_query", query)),
            filters=filters,
            top_k=top_k,
        )


class GeminiAnswerer:
    """LLM-backed grounded answerer with a deterministic fallback."""

    def __init__(self, client: GeminiClient) -> None:
        self._client = client
        self._fallback = MockAnswerer()

    async def answer(self, plan: QueryPlan, results: list[ScoredEvent]) -> ChatAnswer:
        """Generate a grounded answer; fall back to template on failure."""
        if not results:
            return await self._fallback.answer(plan, results)
        context = "\n".join(
            f"- {r.event.name} ({r.event.category.value}, "
            f"{'open' if r.event.open_now else 'closed'})"
            for r in results
        )
        prompt = f"User question: {plan.original_query}\nResults:\n{context}"
        try:
            text = await self._client.generate_text(_ANSWER_SYSTEM, prompt)
        except Exception:  # noqa: BLE001 - degrade gracefully
            return await self._fallback.answer(plan, results)
        citations = [Citation(event_id=r.event.id, name=r.event.name) for r in results]
        return ChatAnswer(
            answer=text.strip(),
            language=plan.detected_language,
            citations=citations,
            results=results,
        )
