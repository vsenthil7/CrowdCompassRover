"""Unit tests for the relevance config validation + store."""
from __future__ import annotations

import pytest

from app.admin.relevance import RelevanceConfig, RelevanceConfigStore


def test_defaults_valid():
    cfg = RelevanceConfig()
    cfg.validate()  # no raise
    assert cfg.to_dict()["keyword_weight"] == 0.5


def test_negative_primary_weight_rejected():
    with pytest.raises(ValueError):
        RelevanceConfig(keyword_weight=-0.1).validate()
    with pytest.raises(ValueError):
        RelevanceConfig(vector_weight=-0.1).validate()


def test_negative_rerank_weight_rejected():
    with pytest.raises(ValueError):
        RelevanceConfig(rerank_freshness=-0.1).validate()
    with pytest.raises(ValueError):
        RelevanceConfig(rerank_distance=-0.1).validate()
    with pytest.raises(ValueError):
        RelevanceConfig(rerank_open_now=-0.1).validate()


def test_sum_over_two_rejected():
    with pytest.raises(ValueError):
        RelevanceConfig(keyword_weight=1.5, vector_weight=1.0).validate()


def test_store_get_set_roundtrip():
    store = RelevanceConfigStore()
    assert store.get().keyword_weight == 0.5
    updated = store.set(RelevanceConfig(keyword_weight=0.2, vector_weight=0.8))
    assert updated.keyword_weight == 0.2
    assert store.get().vector_weight == 0.8


def test_store_set_validates():
    store = RelevanceConfigStore()
    with pytest.raises(ValueError):
        store.set(RelevanceConfig(keyword_weight=-1.0))
