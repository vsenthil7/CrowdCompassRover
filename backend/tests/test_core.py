"""Tests for core utilities: config, embedding, geo."""
from __future__ import annotations

import math

from app.core.config import AppMode, Settings, get_settings
from app.core.embedding import EMBED_DIM, cosine, embed
from app.core.geo import haversine_km
from app.models.domain import GeoPoint


def test_settings_cors_list_and_modes():
    s = Settings(app_mode=AppMode.REAL, cors_origins="http://a.com, http://b.com ,")
    assert s.cors_origin_list == ["http://a.com", "http://b.com"]
    assert s.elastic_is_real is True
    assert s.llm_is_real is True


def test_settings_hybrid_mode():
    s = Settings(app_mode=AppMode.HYBRID)
    assert s.elastic_is_real is True
    assert s.llm_is_real is False


def test_settings_mock_mode():
    s = Settings(app_mode=AppMode.MOCK)
    assert s.elastic_is_real is False
    assert s.llm_is_real is False


def test_get_settings_cached():
    assert get_settings() is get_settings()


def test_embed_deterministic_and_unit_length():
    a = embed("halal restaurant near stadium")
    b = embed("halal restaurant near stadium")
    assert a == b
    assert len(a) == EMBED_DIM
    norm = math.sqrt(sum(x * x for x in a))
    assert abs(norm - 1.0) < 1e-6


def test_embed_empty_string():
    assert embed("") == [0.0] * EMBED_DIM


def test_embed_custom_dim():
    assert len(embed("hello world", dim=16)) == 16


def test_cosine_bounds_and_edges():
    a = embed("stadium")
    assert abs(cosine(a, a) - 1.0) < 1e-6
    assert cosine([], [1.0]) == 0.0
    assert cosine([1.0, 2.0], [1.0]) == 0.0
    assert cosine([0.0, 0.0], [0.0, 0.0]) == 0.0
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_haversine_known_distance():
    # New York to Los Angeles ~3936 km.
    nyc = GeoPoint(lat=40.7128, lon=-74.0060)
    la = GeoPoint(lat=34.0522, lon=-118.2437)
    d = haversine_km(nyc, la)
    assert 3900 < d < 4000


def test_haversine_zero():
    p = GeoPoint(lat=10.0, lon=20.0)
    assert haversine_km(p, p) < 1e-9
