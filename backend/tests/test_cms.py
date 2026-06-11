"""Tests for the multilingual CMS store + models."""
from __future__ import annotations

import pytest

from app.cms.models import VenueContent, VenueTranslation
from app.cms.store import CmsError, CmsStore


def _t(venue="v1", locale="ar", name="ملعب"):
    return VenueTranslation(venue_id=venue, locale=locale, name=name, description="desc")


def test_upsert_and_get_translation():
    store = CmsStore()
    store.upsert_translation(_t())
    got = store.get_translation("v1", "ar")
    assert got is not None
    assert got.name == "ملعب"


def test_upsert_overwrites_same_locale():
    store = CmsStore()
    store.upsert_translation(_t(name="old"))
    store.upsert_translation(_t(name="new"))
    assert store.get_translation("v1", "ar").name == "new"


def test_multiple_locales_for_one_venue():
    store = CmsStore()
    store.upsert_translation(_t(locale="ar"))
    store.upsert_translation(_t(locale="fr", name="Stade"))
    translations = store.get_translations("v1")
    assert set(translations.keys()) == {"ar", "fr"}


def test_unsupported_locale_rejected():
    store = CmsStore()
    with pytest.raises(CmsError):
        store.upsert_translation(_t(locale="zz"))


def test_get_translations_unknown_venue_empty():
    assert CmsStore().get_translations("nope") == {}
    assert CmsStore().get_translation("nope", "ar") is None


def test_all_venues():
    store = CmsStore()
    store.upsert_translation(_t(venue="v1"))
    store.upsert_translation(_t(venue="v2"))
    assert set(store.all_venues()) == {"v1", "v2"}


def test_venue_content_dataclass():
    c = VenueContent("v1")
    c.add(_t())
    assert c.get("ar").venue_id == "v1"
    assert c.get("missing") is None


def test_translation_to_dict():
    d = _t().to_dict()
    assert d["locale"] == "ar"
    assert d["tags"] == []
