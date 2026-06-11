"""Search pipeline: spell-correct → expand → retrieve → rerank.

Sits between the orchestrator and the (resilient) search provider, applying the ranking
enhancements as configured. Each stage is independently toggleable so behaviour can be
tuned or disabled per environment without code changes.
"""
from __future__ import annotations

from app.models.domain import QueryPlan, ScoredEvent
from app.ranking.query_expansion import expand_terms
from app.ranking.reranker import RerankWeights, rerank
from app.ranking.spell import SpellCorrector
from app.services.search_provider import SearchProvider


class SearchPipeline:
    """Composes ranking enhancements around a search provider."""

    def __init__(
        self,
        provider: SearchProvider,
        *,
        spell: SpellCorrector | None = None,
        expand: bool = True,
        do_rerank: bool = True,
        weights: RerankWeights | None = None,
    ) -> None:
        self._provider = provider
        self._spell = spell
        self._expand = expand
        self._rerank = do_rerank
        self._weights = weights

    def _prepare(self, plan: QueryPlan) -> QueryPlan:
        """Apply spell correction and query expansion to the plan's text fields."""
        normalized = plan.normalized_query
        semantic = plan.semantic_text
        if self._spell is not None:
            normalized = self._spell.correct(normalized)
            semantic = self._spell.correct(semantic)
        if self._expand:
            semantic = expand_terms(semantic)
        if normalized == plan.normalized_query and semantic == plan.semantic_text:
            return plan
        return plan.model_copy(
            update={"normalized_query": normalized, "semantic_text": semantic}
        )

    async def run(self, plan: QueryPlan) -> list[ScoredEvent]:
        """Execute the full pipeline for a plan."""
        prepared = self._prepare(plan)
        results = await self._provider.search(prepared)
        if self._rerank and results:
            results = rerank(prepared, results, self._weights)
            results = results[: plan.top_k]
        return results

    async def list_indices(self) -> list[str]:
        """Pass through index listing."""
        return await self._provider.list_indices()
