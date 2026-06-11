"""Tests for query expansion, spell correction, and reranking."""
from __future__ import annotations

from app.models.domain import (
    CityEvent,
    GeoPoint,
    QueryPlan,
    ScoredEvent,
    SearchFilters,
    VenueCategory,
)
from app.ranking.query_expansion import expand_terms, synonyms_for
from app.ranking.reranker import RerankWeights, rerank
from app.ranking.spell import SpellCorrector, levenshtein


# --- query expansion ---


def test_expand_adds_synonyms():
    out = expand_terms("metro")
    assert "subway" in out
    assert "metro" in out


def test_expand_dedups_and_bounds():
    out = expand_terms("metro subway").split()
    assert len(out) == len(set(out))


def test_expand_unknown_token_unchanged():
    assert expand_terms("xyzzy") == "xyzzy"


def test_synonyms_for():
    assert "subway" in synonyms_for("metro")
    assert synonyms_for("nothing") == []


# --- spell ---


def test_levenshtein_basic():
    assert levenshtein("kitten", "kitten") == 0
    assert levenshtein("kitten", "sitten") == 1
    assert levenshtein("kitten", "sitting") == 3


def test_levenshtein_max_distance_shortcut():
    assert levenshtein("abcdef", "uvwxyz", max_distance=2) == 3  # exceeds budget


def test_levenshtein_length_gap_shortcut():
    assert levenshtein("a", "abcdef", max_distance=2) == 3


def test_spell_corrects_typo():
    sc = SpellCorrector({"stadium", "restaurant"}, max_distance=2)
    assert sc.correct_token("stadiom") == "stadium"


def test_spell_leaves_known_and_short_tokens():
    sc = SpellCorrector({"stadium"})
    assert sc.correct_token("stadium") == "stadium"
    assert sc.correct_token("abc") == "abc"  # too short


def test_spell_leaves_unmatchable():
    sc = SpellCorrector({"stadium"}, max_distance=1)
    assert sc.correct_token("zzzzzzzz") == "zzzzzzzz"


def test_spell_correct_phrase():
    sc = SpellCorrector({"stadium", "halal"}, max_distance=2)
    assert sc.correct("stadiom halaal") == "stadium halal"


def test_spell_from_events():
    events = [
        CityEvent(
            id="e",
            name="Big Stadium",
            category=VenueCategory.STADIUM,
            city="Testville",
            description="d",
            location=GeoPoint(lat=0, lon=0),
        )
    ]
    sc = SpellCorrector.from_events(events)
    assert sc.correct_token("stadiom") == "stadium"


# --- rerank ---


def _hit(eid, score, open_now=True, dist=None, capacity=None):
    return ScoredEvent(
        event=CityEvent(
            id=eid,
            name=eid,
            category=VenueCategory.RESTAURANT,
            city="X",
            description="d",
            location=GeoPoint(lat=0, lon=0),
            open_now=open_now,
            capacity=capacity,
        ),
        score=score,
        distance_km=dist,
    )


def _plan():
    return QueryPlan(
        original_query="q",
        detected_language="en",
        normalized_query="food",
        semantic_text="food",
        filters=SearchFilters(),
        top_k=5,
    )


def test_rerank_boosts_open_over_closed():
    results = [_hit("closed", 0.8, open_now=False), _hit("open", 0.8, open_now=True)]
    out = rerank(_plan(), results)
    assert out[0].event.id == "open"


def test_rerank_proximity_boost():
    results = [_hit("far", 0.8, dist=9.0), _hit("near", 0.8, dist=0.5)]
    out = rerank(_plan(), results)
    assert out[0].event.id == "near"


def test_rerank_capacity_boost():
    results = [_hit("small", 0.8, capacity=1000), _hit("big", 0.8, capacity=80000)]
    out = rerank(_plan(), results)
    assert out[0].event.id == "big"


def test_rerank_empty():
    assert rerank(_plan(), []) == []


def test_rerank_custom_weights():
    w = RerankWeights(open_now_boost=0.0, proximity_boost=0.0, capacity_boost=0.0)
    results = [_hit("a", 0.9), _hit("b", 0.5)]
    out = rerank(_plan(), results, w)
    assert out[0].event.id == "a"  # pure relevance


def test_rerank_none_distance_neutral():
    results = [_hit("a", 0.8, dist=None)]
    out = rerank(_plan(), results)
    assert out[0].event.id == "a"
