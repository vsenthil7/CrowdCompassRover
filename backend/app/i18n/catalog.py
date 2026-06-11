"""Internationalisation catalog and translator.

Centralises all user-facing strings keyed by message id and language, replacing the
ad-hoc dicts previously embedded in the answerer. Falls back to English for unknown
languages or missing keys, and supports simple positional formatting.
"""
from __future__ import annotations

SUPPORTED_LANGUAGES = ("en", "es", "fr", "pt", "de", "ar")

# message_id -> { language -> template }
_CATALOG: dict[str, dict[str, str]] = {
    "results.lead_in": {
        "en": "Here is what I found",
        "es": "Esto es lo que encontré",
        "fr": "Voici ce que j'ai trouvé",
        "pt": "Aqui está o que encontrei",
        "de": "Folgendes habe ich gefunden",
        "ar": "إليك ما وجدته",
    },
    "results.none": {
        "en": "I could not find anything matching that right now.",
        "es": "No encontré nada que coincida en este momento.",
        "fr": "Je n'ai rien trouvé correspondant pour le moment.",
        "pt": "Não encontrei nada correspondente no momento.",
        "de": "Ich konnte derzeit nichts Passendes finden.",
        "ar": "لم أتمكن من العثور على شيء مطابق الآن.",
    },
    "status.open": {
        "en": "open", "es": "abierto", "fr": "ouvert",
        "pt": "aberto", "de": "geöffnet", "ar": "مفتوح",
    },
    "status.closed": {
        "en": "closed", "es": "cerrado", "fr": "fermé",
        "pt": "fechado", "de": "geschlossen", "ar": "مغلق",
    },
    "route.cheapest": {
        "en": "Cheapest route", "es": "Ruta más barata", "fr": "Itinéraire le moins cher",
        "pt": "Rota mais barata", "de": "Günstigste Route", "ar": "أرخص طريق",
    },
    "route.summary": {
        "en": "{mode}: {minutes} min, {cost} {currency}",
        "es": "{mode}: {minutes} min, {cost} {currency}",
        "fr": "{mode} : {minutes} min, {cost} {currency}",
        "pt": "{mode}: {minutes} min, {cost} {currency}",
        "de": "{mode}: {minutes} Min, {cost} {currency}",
        "ar": "{mode}: {minutes} د، {cost} {currency}",
    },
}


class Translator:
    """Resolves message ids to localized strings with English fallback."""

    def __init__(self, default: str = "en") -> None:
        self.default = default

    def normalize(self, language: str | None) -> str:
        """Return a supported language code, defaulting when unknown."""
        if language in SUPPORTED_LANGUAGES:
            return language
        return self.default

    def get(self, message_id: str, language: str | None = None, **fmt: object) -> str:
        """Return the localized string for a message id."""
        lang = self.normalize(language)
        entry = _CATALOG.get(message_id, {})
        template = entry.get(lang) or entry.get(self.default) or message_id
        if fmt:
            return template.format(**fmt)
        return template

    def supports(self, language: str | None) -> bool:
        """Whether a language has explicit (non-fallback) support."""
        return language in SUPPORTED_LANGUAGES


_translator = Translator()


def get_translator() -> Translator:
    """Return the shared translator instance."""
    return _translator
