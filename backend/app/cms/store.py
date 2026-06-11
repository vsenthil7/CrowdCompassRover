"""In-memory CMS content store (a durable adapter would replace this in production)."""
from __future__ import annotations

from app.cms.models import SUPPORTED_LOCALES, VenueContent, VenueTranslation


class CmsError(ValueError):
    """Raised for invalid CMS operations (e.g. unsupported locale)."""


class CmsStore:
    """Stores multilingual venue content keyed by venue_id."""

    def __init__(self) -> None:
        self._content: dict[str, VenueContent] = {}

    def upsert_translation(self, translation: VenueTranslation) -> VenueTranslation:
        if translation.locale not in SUPPORTED_LOCALES:
            raise CmsError(f"unsupported locale: {translation.locale}")
        content = self._content.setdefault(
            translation.venue_id, VenueContent(translation.venue_id)
        )
        content.add(translation)
        return translation

    def get_translations(self, venue_id: str) -> dict[str, VenueTranslation]:
        content = self._content.get(venue_id)
        return content.translations if content else {}

    def get_translation(self, venue_id: str, locale: str):
        content = self._content.get(venue_id)
        return content.get(locale) if content else None

    def all_venues(self) -> list[str]:
        return list(self._content.keys())
