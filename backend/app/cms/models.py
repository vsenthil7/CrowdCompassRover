"""CMS domain models for multilingual venue content."""
from __future__ import annotations

from dataclasses import dataclass, field

# The locales the agent actually supports (matches the i18n catalog).
SUPPORTED_LOCALES = {"en", "es", "pt", "fr", "de", "ar"}


@dataclass
class VenueTranslation:
    """One locale variant of a venue's content."""

    venue_id: str
    locale: str
    name: str
    description: str
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "venue_id": self.venue_id,
            "locale": self.locale,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
        }


@dataclass
class VenueContent:
    """All locale variants for a venue."""

    venue_id: str
    translations: dict[str, VenueTranslation] = field(default_factory=dict)

    def add(self, t: VenueTranslation) -> None:
        self.translations[t.locale] = t

    def get(self, locale: str) -> VenueTranslation | None:
        return self.translations.get(locale)
