"""Grounded answer generation.

Turns ranked search hits into a concise, cited, language-matched answer. ``MockAnswerer``
is deterministic and offline; ``GeminiAnswerer`` delegates to the LLM in REAL mode. All
user-facing strings come from the i18n catalog rather than being embedded here.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.i18n.catalog import Translator, get_translator
from app.models.domain import Citation, ChatAnswer, QueryPlan, ScoredEvent


@runtime_checkable
class Answerer(Protocol):
    """Produces a grounded :class:`ChatAnswer` from results."""

    async def answer(self, plan: QueryPlan, results: list[ScoredEvent]) -> ChatAnswer:
        """Return a grounded answer for the plan and results."""
        ...


class MockAnswerer:
    """Deterministic, template-based grounded answerer."""

    def __init__(self, translator: Translator | None = None) -> None:
        self._t = translator or get_translator()

    async def answer(self, plan: QueryPlan, results: list[ScoredEvent]) -> ChatAnswer:
        """Compose a concise cited answer in the detected language."""
        lang = self._t.normalize(plan.detected_language)
        if not results:
            return ChatAnswer(
                answer=self._t.get("results.none", lang),
                language=lang,
                citations=[],
                results=[],
            )

        lines: list[str] = [f"{self._t.get('results.lead_in', lang)}:"]
        citations: list[Citation] = []
        for i, hit in enumerate(results, start=1):
            ev = hit.event
            dist = f" ({hit.distance_km:.1f} km)" if hit.distance_km is not None else ""
            status_key = "status.open" if ev.open_now else "status.closed"
            status = self._t.get(status_key, lang)
            lines.append(f"{i}. {ev.name} — {ev.category.value}, {status}{dist}")
            citations.append(Citation(event_id=ev.id, name=ev.name))

        return ChatAnswer(
            answer="\n".join(lines),
            language=lang,
            citations=citations,
            results=results,
        )
