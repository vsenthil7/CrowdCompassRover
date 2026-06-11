"""Live hybrid-relevance weight management.

Holds the tunable weights that feed the hybrid query builder (keyword vs vector) and the
availability-aware reranker (freshness / distance / open-now). An admin can read and update
them at runtime via the relevance API; the holder is injected through the composition root so
there is no module-global shared state across requests or tests.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RelevanceConfig:
    """Current hybrid-search + rerank weights."""

    keyword_weight: float = 0.5
    vector_weight: float = 0.5
    rerank_freshness: float = 0.3
    rerank_distance: float = 0.2
    rerank_open_now: float = 0.5

    def validate(self) -> None:
        if self.keyword_weight < 0 or self.vector_weight < 0:
            raise ValueError("weights must be non-negative")
        if self.rerank_freshness < 0 or self.rerank_distance < 0 or self.rerank_open_now < 0:
            raise ValueError("rerank weights must be non-negative")
        if self.keyword_weight + self.vector_weight > 2.0:
            raise ValueError("keyword_weight + vector_weight must be <= 2.0")

    def to_dict(self) -> dict:
        return {
            "keyword_weight": self.keyword_weight,
            "vector_weight": self.vector_weight,
            "rerank_freshness": self.rerank_freshness,
            "rerank_distance": self.rerank_distance,
            "rerank_open_now": self.rerank_open_now,
        }


class RelevanceConfigStore:
    """Mutable holder for the active relevance config (validated on update)."""

    def __init__(self, config: RelevanceConfig | None = None) -> None:
        self._config = config or RelevanceConfig()

    def get(self) -> RelevanceConfig:
        return self._config

    def set(self, config: RelevanceConfig) -> RelevanceConfig:
        config.validate()
        self._config = config
        return self._config
