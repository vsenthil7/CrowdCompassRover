"""Hybrid scoring used by the in-memory mock provider.

Combines a BM25-style keyword score with vector cosine similarity, then applies
structured filters (category, open-now, dietary, geo distance). The real Elastic
provider expresses the same intent as a hybrid query DSL + ES|QL, but we keep an
explicit Python implementation so MOCK mode produces meaningful, deterministic ranking.
"""
from __future__ import annotations

import math
from collections import Counter

from app.core.embedding import cosine, embed
from app.core.geo import haversine_km
from app.models.domain import CityEvent, QueryPlan, ScoredEvent, SearchFilters

KEYWORD_WEIGHT = 0.5
VECTOR_WEIGHT = 0.5


def _bm25ish(query_terms: list[str], doc: CityEvent, corpus_df: Counter, n_docs: int) -> float:
    """A compact BM25-style keyword relevance score."""
    if not query_terms:
        return 0.0
    blob_terms = doc.text_blob().split()
    if not blob_terms:  # pragma: no cover - CityEvent always has a name token
        return 0.0
    tf = Counter(blob_terms)
    doc_len = len(blob_terms)
    avg_len = 12.0  # stable constant for deterministic scoring
    k1, b = 1.5, 0.75
    score = 0.0
    for term in query_terms:
        if term not in tf:
            continue
        df = corpus_df.get(term, 1)
        idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
        freq = tf[term]
        denom = freq + k1 * (1 - b + b * doc_len / avg_len)
        score += idf * (freq * (k1 + 1)) / denom
    return score


def _passes_filters(doc: CityEvent, f: SearchFilters) -> tuple[bool, float | None]:
    """Return (passes, distance_km) after applying structured filters."""
    if f.city and doc.city.lower() != f.city.lower():
        return False, None
    if f.category and doc.category != f.category:
        return False, None
    if f.open_now is not None and doc.open_now != f.open_now:
        return False, None
    if f.halal is not None and doc.halal != f.halal:
        return False, None
    if f.vegetarian is not None and doc.vegetarian != f.vegetarian:
        return False, None
    if (
        f.wheelchair_accessible is not None
        and doc.wheelchair_accessible != f.wheelchair_accessible
    ):
        return False, None
    distance = None
    if f.near is not None:
        distance = haversine_km(f.near, doc.location)
        if f.max_distance_km is not None and distance > f.max_distance_km:
            return False, distance
    return True, distance


def hybrid_rank(plan: QueryPlan, docs: list[CityEvent]) -> list[ScoredEvent]:
    """Rank documents for a query plan using keyword + vector + filters."""
    n_docs = len(docs)
    corpus_df: Counter = Counter()
    for d in docs:
        for term in set(d.text_blob().split()):
            corpus_df[term] += 1

    query_terms = (plan.normalized_query + " " + plan.semantic_text).lower().split()
    q_vec = embed(plan.semantic_text or plan.normalized_query)

    # Pre-compute keyword scores for normalisation.
    raw: list[tuple[CityEvent, float, float, float | None]] = []
    max_kw = 0.0
    for doc in docs:
        passes, distance = _passes_filters(doc, plan.filters)
        if not passes:
            continue
        kw = _bm25ish(query_terms, doc, corpus_df, n_docs)
        max_kw = max(max_kw, kw)
        doc_vec = doc.embedding if doc.embedding else embed(doc.text_blob())
        vec = (cosine(q_vec, doc_vec) + 1) / 2  # map [-1,1] -> [0,1]
        raw.append((doc, kw, vec, distance))

    scored: list[ScoredEvent] = []
    for doc, kw, vec, distance in raw:
        norm_kw = kw / max_kw if max_kw > 0 else 0.0
        score = KEYWORD_WEIGHT * norm_kw + VECTOR_WEIGHT * vec
        scored.append(ScoredEvent(event=doc, score=round(score, 6), distance_km=distance))

    scored.sort(key=lambda s: (s.score, -(s.distance_km or 0)), reverse=True)
    return scored[: plan.top_k]
