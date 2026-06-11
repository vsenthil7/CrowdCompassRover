"""Translate a :class:`QueryPlan` into an Elasticsearch hybrid query DSL body.

The same plan that drives the mock ranker drives the real query, so behaviour is aligned
across modes. Filters become a bool/filter context; keyword + kNN vector form the hybrid
relevance. User input is never passed as raw DSL — it is always structured here.
"""
from __future__ import annotations

from typing import Any

from app.core.embedding import embed
from app.models.domain import QueryPlan, SearchFilters


def _filter_clauses(f: SearchFilters) -> list[dict[str, Any]]:
    clauses: list[dict[str, Any]] = []
    if f.city:
        clauses.append({"term": {"city": f.city}})
    if f.category:
        clauses.append({"term": {"category": f.category.value}})
    if f.open_now is not None:
        clauses.append({"term": {"open_now": f.open_now}})
    if f.halal is not None:
        clauses.append({"term": {"halal": f.halal}})
    if f.vegetarian is not None:
        clauses.append({"term": {"vegetarian": f.vegetarian}})
    if f.wheelchair_accessible is not None:
        clauses.append({"term": {"wheelchair_accessible": f.wheelchair_accessible}})
    if f.near is not None and f.max_distance_km is not None:
        clauses.append(
            {
                "geo_distance": {
                    "distance": f"{f.max_distance_km}km",
                    "location": {"lat": f.near.lat, "lon": f.near.lon},
                }
            }
        )
    return clauses


def build_query(plan: QueryPlan) -> dict[str, Any]:
    """Build a hybrid (keyword + kNN) ES query body for the plan."""
    query_vector = embed(plan.semantic_text or plan.normalized_query)
    filters = _filter_clauses(plan.filters)
    keyword = {
        "multi_match": {
            "query": plan.normalized_query,
            "fields": ["name^2", "description", "tags", "category"],
            "type": "best_fields",
        }
    }
    body: dict[str, Any] = {
        "size": plan.top_k,
        "query": {"bool": {"must": [keyword], "filter": filters}},
        "knn": {
            "field": "embedding",
            "query_vector": query_vector,
            "k": plan.top_k,
            "num_candidates": max(50, plan.top_k * 10),
            "filter": filters,
        },
    }
    return body
