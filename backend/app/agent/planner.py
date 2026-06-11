"""Query planning: natural language -> structured :class:`QueryPlan`.

``MockPlanner`` is a deterministic, rule-based, multilingual planner used offline and in
tests. ``GeminiPlanner`` (see gemini_planner.py) delegates to the LLM in REAL mode. Both
satisfy :class:`Planner`.
"""
from __future__ import annotations

import re
from typing import Protocol, runtime_checkable

from app.agent.lexicon import (
    CATEGORY_TERMS,
    CITY_TERMS,
    HALAL_TERMS,
    LANGUAGE_MARKERS,
    NORMALISE,
    OPEN_NOW_TERMS,
    VEGETARIAN_TERMS,
)
from app.models.domain import GeoPoint, QueryPlan, SearchFilters

_WORD_RE = re.compile(r"[a-zA-Z\u00C0-\u024F]+")


@runtime_checkable
class Planner(Protocol):
    """Produces a structured query plan from raw user text."""

    async def plan(
        self, query: str, user_location: GeoPoint | None, top_k: int
    ) -> QueryPlan:
        """Return a :class:`QueryPlan` for the query."""
        ...


def detect_language(tokens: list[str]) -> str:
    """Marker-based language detection.

    Counts distinctive marker hits per language. Ties (including the common case where a
    query shares words with English) resolve to English, the tournament lingua franca.
    """
    token_set = set(tokens)
    scores: dict[str, int] = {
        lang: sum(1 for m in markers if m in token_set)
        for lang, markers in LANGUAGE_MARKERS.items()
    }
    best_score = max(scores.values())
    if best_score == 0:
        return "en"
    # English wins ties to avoid loanword/cognate false positives.
    if scores.get("en", 0) == best_score:
        return "en"
    for lang, score in scores.items():
        if score == best_score:
            return lang
    return "en"  # pragma: no cover - unreachable given best_score>0


class MockPlanner:
    """Deterministic multilingual planner."""

    async def plan(
        self, query: str, user_location: GeoPoint | None, top_k: int
    ) -> QueryPlan:
        """Extract language, filters and a normalised query deterministically."""
        lowered = query.lower()
        tokens = _WORD_RE.findall(lowered)
        language = detect_language(tokens)

        filters = SearchFilters()

        # City detection (multi-word first), matched on word boundaries to avoid
        # short aliases (e.g. "la") matching inside unrelated words ("halal").
        padded = f" {lowered} "
        for phrase, city in CITY_TERMS.items():
            if f" {phrase} " in padded:
                filters.city = city
                break

        # Category detection.
        for tok in tokens:
            if tok in CATEGORY_TERMS:
                filters.category = CATEGORY_TERMS[tok]
                break

        # Open-now.
        if any(tok in OPEN_NOW_TERMS for tok in tokens):
            filters.open_now = True

        # Dietary.
        if any(tok in HALAL_TERMS for tok in tokens):
            filters.halal = True
        if any(tok in VEGETARIAN_TERMS for tok in tokens):
            filters.vegetarian = True

        # Proximity: if user gave a location and asked for "near"/route.
        near_terms = {"near", "nearest", "close", "cerca", "perto", "nahe", "route", "ruta"}
        if user_location is not None and any(t in near_terms for t in tokens):
            filters.near = user_location
            filters.max_distance_km = 25.0

        normalized = " ".join(NORMALISE.get(tok, tok) for tok in tokens)
        semantic = normalized

        return QueryPlan(
            original_query=query,
            detected_language=language,
            normalized_query=normalized,
            semantic_text=semantic,
            filters=filters,
            top_k=top_k,
        )
