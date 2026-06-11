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


def build_query(
    plan: QueryPlan,
    *,
    keyword_weight: float = 0.5,
    vector_weight: float = 0.5,
    rrf_window_size: int = 100,
) -> dict[str, Any]:
    """Build a hybrid (keyword + kNN) ES query body for the plan.

    Uses Elasticsearch 8.x Reciprocal Rank Fusion (``rank.rrf``) to merge the BM25 and kNN
    result lists. ``keyword_weight`` / ``vector_weight`` are injectable so a relevance-tuning
    layer can override them at runtime. The ``open_now`` boost raises currently-open venues
    via a ``should`` clause (boost only, never a hard filter).
    """
    query_vector = embed(plan.semantic_text or plan.normalized_query)
    filters = _filter_clauses(plan.filters)

    should_clauses: list[dict[str, Any]] = []
    if plan.filters.open_now is True:
        should_clauses.append({"term": {"open_now": {"value": True, "boost": 2.0}}})

    keyword: dict[str, Any] = {
        "multi_match": {
            "query": plan.normalized_query,
            "fields": ["name^3", "description^1", "tags^1.5", "category^0.5"],
            "type": "best_fields",
            "fuzziness": "AUTO",
            "boost": keyword_weight,
        }
    }

    bool_query: dict[str, Any] = {"must": [keyword], "filter": filters}
    if should_clauses:
        bool_query["should"] = should_clauses
        bool_query["minimum_should_match"] = 0  # boost only, not required

    knn_clause: dict[str, Any] = {
        "field": "embedding",
        "query_vector": query_vector,
        "k": min(plan.top_k * 2, rrf_window_size),
        "num_candidates": max(50, plan.top_k * 10),
        "boost": vector_weight,
        "filter": filters,
    }

    body: dict[str, Any] = {
        "size": plan.top_k,
        "query": {"bool": bool_query},
        "knn": knn_clause,
        # RRF merges the BM25 and kNN rank lists into a single score.
        "rank": {"rrf": {"window_size": rrf_window_size, "rank_constant": 60}},
    }
    return body
