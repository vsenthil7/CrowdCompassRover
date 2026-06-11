"""Tests for persistence repositories and i18n catalog."""
from __future__ import annotations

from app.i18n.catalog import SUPPORTED_LANGUAGES, Translator, get_translator
from app.models.domain import CityEvent, GeoPoint, VenueCategory
from app.persistence.memory import InMemoryEventRepository, InMemoryRepository


def _event(eid="e1", city="New York"):
    return CityEvent(
        id=eid,
        name=f"Venue {eid}",
        category=VenueCategory.STADIUM,
        city=city,
        description="d",
        location=GeoPoint(lat=0, lon=0),
    )


# --- generic repo ---


async def test_inmemory_repo_crud():
    repo: InMemoryRepository[str, int] = InMemoryRepository()
    assert await repo.get("a") is None
    await repo.put("a", 1)
    assert await repo.get("a") == 1
    assert await repo.count() == 1
    assert await repo.list_all() == [1]
    assert await repo.delete("a") is True
    assert await repo.delete("a") is False


# --- event repo ---


async def test_event_repo_seeded():
    repo = InMemoryEventRepository([_event("a"), _event("b", city="LA")])
    assert await repo.count() == 2
    assert (await repo.get("a")).id == "a"


async def test_event_repo_put_and_bulk():
    repo = InMemoryEventRepository()
    await repo.put("a", _event("a"))
    written = await repo.bulk_put([_event("b"), _event("c")])
    assert written == 2
    assert await repo.count() == 3
    assert len(await repo.list_all()) == 3


async def test_event_repo_by_city_case_insensitive():
    repo = InMemoryEventRepository([_event("a", "New York"), _event("b", "Los Angeles")])
    nyc = await repo.by_city("new york")
    assert len(nyc) == 1
    assert nyc[0].id == "a"


async def test_event_repo_get_missing():
    repo = InMemoryEventRepository()
    assert await repo.get("nope") is None


# --- i18n ---


def test_translator_known_language():
    t = Translator()
    assert t.get("results.lead_in", "es") == "Esto es lo que encontré"


def test_translator_fallback_unknown_language():
    t = Translator()
    assert t.get("results.lead_in", "zz") == "Here is what I found"


def test_translator_fallback_unknown_key():
    t = Translator()
    assert t.get("missing.key", "en") == "missing.key"


def test_translator_normalize():
    t = Translator()
    assert t.normalize("fr") == "fr"
    assert t.normalize("zz") == "en"
    assert t.normalize(None) == "en"


def test_translator_supports():
    t = Translator()
    assert t.supports("ar") is True
    assert t.supports("zz") is False


def test_translator_formatting():
    t = Translator()
    # status keys carry no placeholders, but format path must be exercised.
    assert t.get("status.open", "en") == "open"


def test_translator_formatting_with_placeholders():
    t = Translator()
    out = t.get("route.summary", "en", mode="Transit", minutes=15, cost=2.5, currency="USD")
    assert out == "Transit: 15 min, 2.5 USD"


def test_supported_languages_constant():
    assert "en" in SUPPORTED_LANGUAGES
    assert len(SUPPORTED_LANGUAGES) == 6


def test_get_translator_singleton():
    assert get_translator() is get_translator()
