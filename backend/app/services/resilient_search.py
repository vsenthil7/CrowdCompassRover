"""A decorator SearchProvider adding caching, retry, circuit-breaking and metrics.

Wraps any concrete :class:`SearchProvider` (mock or Elastic) so resilience concerns live
in one composable place rather than being scattered through the providers. Search results
are cached by plan; list/mapping calls pass through with retry + breaker protection.
"""
from __future__ import annotations

import logging

from app.errors.exceptions import UpstreamUnavailableError
from app.models.domain import QueryPlan, ScoredEvent
from app.observability.logging_config import get_logger, log_event
from app.observability.metrics import MetricsRegistry
from app.resilience.cache import TTLCache
from app.resilience.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.resilience.retry import RetryPolicy, retry_async
from app.services.search_provider import SearchProvider

_logger = get_logger("search.resilient")


def _plan_key(plan: QueryPlan) -> str:
    """A stable cache key for a plan (semantics + filters + top_k)."""
    f = plan.filters.model_dump()
    return "|".join(
        [
            plan.normalized_query,
            plan.semantic_text,
            str(sorted((k, str(v)) for k, v in f.items() if v is not None)),
            str(plan.top_k),
        ]
    )


class ResilientSearchProvider:
    """Composable resilience wrapper around a SearchProvider."""

    def __init__(
        self,
        inner: SearchProvider,
        *,
        cache: TTLCache,
        breaker: CircuitBreaker,
        retry_policy: RetryPolicy,
        metrics: MetricsRegistry,
    ) -> None:
        self._inner = inner
        self._cache = cache
        self._breaker = breaker
        self._retry = retry_policy
        self._metrics = metrics

    async def _guarded(self, op):
        """Run op through the breaker + retry, mapping failures to UpstreamUnavailable."""
        async def attempt():
            return await self._breaker.call(op)

        try:
            return await retry_async(
                attempt, self._retry, retry_on=(Exception,)
            )
        except CircuitOpenError as exc:
            self._metrics.inc("search_circuit_open_total")
            raise UpstreamUnavailableError("search backend circuit open") from exc
        except Exception as exc:  # noqa: BLE001 - surface as typed upstream error
            self._metrics.inc("search_upstream_error_total")
            raise UpstreamUnavailableError(str(exc)) from exc

    async def list_indices(self) -> list[str]:
        """List indices with resilience."""
        return await self._guarded(self._inner.list_indices)

    async def get_mappings(self, index: str) -> dict:
        """Get mappings with resilience."""
        return await self._guarded(lambda: self._inner.get_mappings(index))

    async def search(self, plan: QueryPlan) -> list[ScoredEvent]:
        """Search with caching + resilience."""
        key = _plan_key(plan)
        cached = await self._cache.get(key)
        if cached is not None:
            self._metrics.inc("search_cache_total", result="hit")
            return cached
        self._metrics.inc("search_cache_total", result="miss")
        with self._metrics.time("search_backend_seconds"):
            results = await self._guarded(lambda: self._inner.search(plan))
        await self._cache.set(key, results)
        log_event(
            _logger,
            logging.DEBUG,
            "search_executed",
            hits=len(results),
            cache="miss",
        )
        return results
