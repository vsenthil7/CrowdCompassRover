"""Grounded answer generation.

Turns ranked search hits into a concise, cited, language-matched answer. ``MockAnswerer``
is deterministic and offline; ``GeminiAnswerer`` delegates to the LLM in REAL mode.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.models.domain import Citation, ChatAnswer, QueryPlan, ScoredEvent

# Minimal localized lead-ins for the mock answerer.
_LEAD_IN: dict[str, str] = {
    "en": "Here is what I found",
    "es": "Esto es lo que encontré",
    "fr": "Voici ce que j'ai trouvé",
    "pt": "Aqui está o que encontrei",
    "de": "Folgendes habe ich gefunden",
    "ar": "إليك ما وجدته",
}

_NO_RESULTS: dict[str, str] = {
    "en": "I could not find anything matching that right now.",
    "es": "No encontré nada que coincida en este momento.",
    "fr": "Je n'ai rien trouvé correspondant pour le moment.",
    "pt": "Não encontrei nada correspondente no momento.",
    "de": "Ich konnte derzeit nichts Passendes finden.",
    "ar": "لم أتمكن من العثور على شيء مطابق الآن.",
}


@runtime_checkable
class Answerer(Protocol):
    """Produces a grounded :class:`ChatAnswer` from results."""

    async def answer(self, plan: QueryPlan, results: list[ScoredEvent]) -> ChatAnswer:
        """Return a grounded answer for the plan and results."""
        ...


class MockAnswerer:
    """Deterministic, template-based grounded answerer."""

    async def answer(self, plan: QueryPlan, results: list[ScoredEvent]) -> ChatAnswer:
        """Compose a concise cited answer in the detected language."""
        lang = plan.detected_language if plan.detected_language in _LEAD_IN else "en"
        if not results:
            return ChatAnswer(
                answer=_NO_RESULTS[lang],
                language=lang,
                citations=[],
                results=[],
            )

        lead = _LEAD_IN[lang]
        lines: list[str] = [f"{lead}:"]
        citations: list[Citation] = []
        for i, hit in enumerate(results, start=1):
            ev = hit.event
            dist = ""
            if hit.distance_km is not None:
                dist = f" ({hit.distance_km:.1f} km)"
            status = "open" if ev.open_now else "closed"
            lines.append(f"{i}. {ev.name} — {ev.category.value}, {status}{dist}")
            citations.append(Citation(event_id=ev.id, name=ev.name))

        return ChatAnswer(
            answer="\n".join(lines),
            language=lang,
            citations=citations,
            results=results,
        )
