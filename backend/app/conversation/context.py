"""Resolve follow-up turns by carrying forward prior plan context.

When a query is a short refinement ("what about open ones?", "and near the stadium",
"cheaper") that lacks its own category/city, we inherit those from the previous turn's
plan so multi-turn conversations feel coherent. Inheritance only fills *unset* fields, so
an explicit new value always wins.
"""
from __future__ import annotations

from app.models.domain import QueryPlan, SearchFilters

# Tokens that signal a refinement rather than a fresh query.
_REFINEMENT_MARKERS = {
    "what", "about", "and", "also", "instead", "cheaper", "closer", "open",
    "nearer", "ones", "too", "any", "other", "more",
}


def is_refinement(query: str) -> bool:
    """Heuristic: short queries dominated by refinement markers are follow-ups."""
    tokens = query.lower().split()
    if not tokens or len(tokens) > 6:
        return False
    marker_hits = sum(1 for t in tokens if t in _REFINEMENT_MARKERS)
    return marker_hits >= 1


def merge_filters(prior: SearchFilters, current: SearchFilters) -> SearchFilters:
    """Fill unset fields of ``current`` from ``prior``."""
    data = current.model_dump()
    prior_data = prior.model_dump()
    for key, value in data.items():
        if value is None and prior_data.get(key) is not None:
            data[key] = prior_data[key]
    return SearchFilters(**data)


def apply_context(plan: QueryPlan, prior_plan: QueryPlan | None) -> QueryPlan:
    """Return a plan enriched with prior context when the turn is a refinement."""
    if prior_plan is None or not is_refinement(plan.original_query):
        return plan
    merged = merge_filters(prior_plan.filters, plan.filters)
    semantic = plan.semantic_text
    if prior_plan.semantic_text and prior_plan.semantic_text not in semantic:
        semantic = f"{prior_plan.semantic_text} {semantic}".strip()
    return plan.model_copy(update={"filters": merged, "semantic_text": semantic})
