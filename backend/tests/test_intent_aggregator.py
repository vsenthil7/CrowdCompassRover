"""Tests for the intent aggregator."""
from __future__ import annotations

from app.analytics.intent_aggregator import IntentAggregator
from app.analytics.recorder import AnalyticsRecorder


def _recorder() -> AnalyticsRecorder:
    r = AnalyticsRecorder()
    r.record("halal food", "en", 3, category="restaurant", duration_ms=10.0)
    r.record("halal food", "en", 2, category="restaurant", duration_ms=20.0)
    r.record("vegan place", "en", 0, category="restaurant", duration_ms=30.0)
    r.record("stadium route", "en", 1, category="stadium", duration_ms=5.0)
    r.record("mystery", "en", 0)  # no category -> unclassified
    return r


def test_top_intents_groups_by_category():
    agg = IntentAggregator(_recorder())
    intents = {s.intent: s for s in agg.top_intents()}
    assert intents["restaurant"].count == 3
    assert intents["stadium"].count == 1
    assert intents["unclassified"].count == 1


def test_zero_result_count_per_intent():
    agg = IntentAggregator(_recorder())
    intents = {s.intent: s for s in agg.top_intents()}
    assert intents["restaurant"].zero_result_count == 1  # "vegan place"


def test_examples_are_deduped_and_capped():
    agg = IntentAggregator(_recorder())
    rest = next(s for s in agg.top_intents() if s.intent == "restaurant")
    assert "halal food" in rest.example_queries
    assert len(rest.example_queries) <= 3
    # "halal food" recorded twice but appears once.
    assert rest.example_queries.count("halal food") == 1


def test_avg_duration():
    agg = IntentAggregator(_recorder())
    rest = next(s for s in agg.top_intents() if s.intent == "restaurant")
    assert rest.avg_duration_ms == 20.0  # (10+20+30)/3


def test_sorted_by_count_and_top_n():
    agg = IntentAggregator(_recorder())
    out = agg.top_intents(top_n=1)
    assert len(out) == 1
    assert out[0].intent == "restaurant"  # highest count


def test_to_dict():
    agg = IntentAggregator(_recorder())
    d = next(s for s in agg.top_intents() if s.intent == "stadium").to_dict()
    assert d["intent"] == "stadium"
    assert d["count"] == 1


def test_empty_recorder():
    assert IntentAggregator(AnalyticsRecorder()).top_intents() == []
