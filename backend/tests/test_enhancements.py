"""Tests for conversation sessions/context, errors, and search composition."""
from __future__ import annotations

import pytest

from app.conversation.context import apply_context, is_refinement, merge_filters
from app.conversation.session import SessionStore
from app.errors.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitedError,
    RoverError,
    UpstreamUnavailableError,
    ValidationError,
)
from app.models.domain import QueryPlan, SearchFilters, VenueCategory
from app.observability.metrics import MetricsRegistry
from app.resilience.cache import TTLCache
from app.resilience.circuit_breaker import CircuitBreaker
from app.resilience.retry import RetryPolicy
from app.services.mock_search import MockSearchProvider
from app.services.resilient_search import ResilientSearchProvider, _plan_key
from app.services.search_pipeline import SearchPipeline


def _plan(query="halal food", **kw):
    base = dict(
        original_query=query,
        detected_language="en",
        normalized_query="halal food",
        semantic_text="halal food",
        filters=SearchFilters(),
        top_k=5,
    )
    base.update(kw)
    return QueryPlan(**base)


# --- conversation context ---


def test_is_refinement():
    assert is_refinement("what about open ones") is True
    assert is_refinement("halal restaurants near the stadium in mexico city please now") is False
    assert is_refinement("") is False


def test_merge_filters_fills_unset():
    prior = SearchFilters(city="New York", category=VenueCategory.RESTAURANT)
    current = SearchFilters(open_now=True)
    merged = merge_filters(prior, current)
    assert merged.city == "New York"
    assert merged.category == VenueCategory.RESTAURANT
    assert merged.open_now is True


def test_merge_filters_current_wins():
    prior = SearchFilters(city="New York")
    current = SearchFilters(city="Los Angeles")
    assert merge_filters(prior, current).city == "Los Angeles"


def test_apply_context_no_prior():
    plan = _plan()
    assert apply_context(plan, None) is plan


def test_apply_context_non_refinement_unchanged():
    plan = _plan(query="halal food in a totally fresh long query string here")
    prior = _plan(filters=SearchFilters(city="New York"))
    assert apply_context(plan, prior) is plan


def test_apply_context_refinement_inherits():
    prior = _plan(filters=SearchFilters(city="Mexico City", halal=True), semantic_text="halal food")
    plan = _plan(query="what about open ones", filters=SearchFilters(open_now=True), semantic_text="open")
    out = apply_context(plan, prior)
    assert out.filters.city == "Mexico City"
    assert out.filters.halal is True
    assert out.filters.open_now is True
    assert "halal food" in out.semantic_text


# --- session store ---


def test_session_create_and_record():
    clock = {"t": 0.0}
    store = SessionStore(ttl=100.0, clock=lambda: clock["t"])
    store.record("s1", "halal food", _plan())
    session = store.get("s1")
    assert session is not None
    assert session.last_plan is not None
    assert store.active_count == 1


def test_session_expiry():
    clock = {"t": 0.0}
    store = SessionStore(ttl=10.0, clock=lambda: clock["t"])
    store.record("s1", "q", _plan())
    clock["t"] = 20.0
    assert store.get("s1") is None


def test_session_lru_eviction():
    store = SessionStore(maxsize=2, ttl=1000.0)
    store.get_or_create("a")
    store.get_or_create("b")
    store.get("a")
    store.get_or_create("c")  # evicts b
    assert store.get("b") is None
    assert store.get("a") is not None


def test_session_empty_last_plan():
    store = SessionStore()
    session = store.get_or_create("x")
    assert session.last_plan is None


# --- errors ---


def test_rover_error_problem():
    err = RoverError("custom detail")
    problem = err.to_problem(instance="/api/x")
    assert problem["status"] == 500
    assert problem["detail"] == "custom detail"
    assert problem["instance"] == "/api/x"


def test_rover_error_default_detail():
    assert RoverError().detail == "Internal Server Error"


@pytest.mark.parametrize(
    "exc,status",
    [
        (UpstreamUnavailableError(), 503),
        (RateLimitedError(), 429),
        (AuthenticationError(), 401),
        (ValidationError(), 422),
        (NotFoundError(), 404),
    ],
)
def test_typed_errors_status(exc, status):
    assert exc.status_code == status
    assert exc.to_problem()["code"] == exc.code


# --- resilient search ---


def test_plan_key_stable():
    assert _plan_key(_plan()) == _plan_key(_plan())


def _resilient(provider=None):
    return ResilientSearchProvider(
        provider or MockSearchProvider(),
        cache=TTLCache(ttl=100.0),
        breaker=CircuitBreaker("t", fail_max=2, reset_timeout=100.0),
        retry_policy=RetryPolicy(max_attempts=2, base_delay=0.0),
        metrics=MetricsRegistry(),
    )


async def test_resilient_search_caches():
    rs = _resilient()
    plan = _plan()
    first = await rs.search(plan)
    second = await rs.search(plan)
    assert [h.event.id for h in first] == [h.event.id for h in second]


async def test_resilient_list_and_mappings():
    rs = _resilient()
    assert "cc-city-events" in await rs.list_indices()
    mapping = await rs.get_mappings("cc-city-events")
    assert "properties" in mapping


async def test_resilient_maps_failure_to_upstream_error():
    class _Bad:
        async def list_indices(self):
            raise RuntimeError("down")

        async def get_mappings(self, index):
            raise RuntimeError("down")

        async def search(self, plan):
            raise RuntimeError("down")

    rs = _resilient(_Bad())
    with pytest.raises(UpstreamUnavailableError):
        await rs.search(_plan())


async def test_resilient_circuit_open_error():
    class _Bad:
        async def list_indices(self):
            raise RuntimeError("down")

        async def get_mappings(self, index):  # pragma: no cover - not used
            raise RuntimeError("down")

        async def search(self, plan):  # pragma: no cover - not used
            raise RuntimeError("down")

    rs = ResilientSearchProvider(
        _Bad(),
        cache=TTLCache(ttl=100.0),
        breaker=CircuitBreaker("t", fail_max=1, reset_timeout=100.0),
        retry_policy=RetryPolicy(max_attempts=1, base_delay=0.0),
        metrics=MetricsRegistry(),
    )
    # First call trips the breaker (mapped to upstream error).
    with pytest.raises(UpstreamUnavailableError):
        await rs.list_indices()
    # Second call: breaker open -> still upstream error.
    with pytest.raises(UpstreamUnavailableError):
        await rs.list_indices()


# --- search pipeline ---


async def test_pipeline_runs_all_stages():
    from app.ranking.spell import SpellCorrector

    provider = MockSearchProvider()
    spell = SpellCorrector.from_events(provider.events)
    pipeline = SearchPipeline(provider, spell=spell, expand=True, do_rerank=True)
    results = await pipeline.run(_plan(normalized_query="stadiom", semantic_text="stadiom"))
    assert results
    assert await pipeline.list_indices() == ["cc-city-events"]


async def test_pipeline_no_enhancements():
    provider = MockSearchProvider()
    pipeline = SearchPipeline(provider, spell=None, expand=False, do_rerank=False)
    results = await pipeline.run(_plan())
    assert isinstance(results, list)


async def test_pipeline_prepare_unchanged_when_no_ops():
    provider = MockSearchProvider()
    pipeline = SearchPipeline(provider, spell=None, expand=False, do_rerank=False)
    plan = _plan()
    prepared = pipeline._prepare(plan)
    assert prepared is plan
