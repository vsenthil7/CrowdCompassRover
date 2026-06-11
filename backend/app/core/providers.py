"""Provider factory — assembles the full agent stack from settings.

This is the single composition root. ``APP_MODE`` decides mock vs real for search and LLM;
configuration flags toggle ranking enhancements; resilience (cache/retry/breaker) and
conversation sessions are wired here so no other module needs to know how they fit
together.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.agent.answerer import Answerer, MockAnswerer
from app.agent.gemini_client import GeminiClient
from app.agent.gemini_planner import GeminiAnswerer, GeminiPlanner
from app.agent.orchestrator import RoverAgent
from app.agent.planner import MockPlanner, Planner
from app.conversation.session import SessionStore
from app.core.config import Settings
from app.data.fixtures import load_fixture_events
from app.mcp.elastic_client import ElasticMCPClient
from app.observability.metrics import get_metrics
from app.ranking.reranker import RerankWeights
from app.ranking.spell import SpellCorrector
from app.resilience.cache import TTLCache
from app.resilience.circuit_breaker import CircuitBreaker
from app.resilience.retry import RetryPolicy
from app.services.elastic_search import ElasticSearchProvider
from app.services.mock_search import MockSearchProvider
from app.services.resilient_search import ResilientSearchProvider
from app.services.search_pipeline import SearchPipeline
from app.services.search_provider import SearchProvider


@dataclass
class Components:
    """Constructed components plus any closables needing shutdown."""

    agent: RoverAgent
    sessions: SessionStore
    closables: list[object]


def build_base_search_provider(settings: Settings) -> tuple[SearchProvider, list[object]]:
    """Build the concrete (un-wrapped) search provider for the active mode."""
    closables: list[object] = []
    if settings.elastic_is_real and settings.elastic_mcp_url and settings.elastic_mcp_api_key:
        client = ElasticMCPClient(settings.elastic_mcp_url, settings.elastic_mcp_api_key)
        closables.append(client)
        return ElasticSearchProvider(client, settings.elastic_index), closables
    return MockSearchProvider(), closables


def wrap_resilient(provider: SearchProvider, settings: Settings) -> ResilientSearchProvider:
    """Wrap a provider with cache + retry + circuit breaker + metrics."""
    return ResilientSearchProvider(
        provider,
        cache=TTLCache(maxsize=settings.cache_maxsize, ttl=settings.cache_ttl),
        breaker=CircuitBreaker(
            "search",
            fail_max=settings.circuit_fail_max,
            reset_timeout=settings.circuit_reset_timeout,
        ),
        retry_policy=RetryPolicy(max_attempts=settings.retry_max_attempts),
        metrics=get_metrics(),
    )


def build_pipeline(provider: SearchProvider, settings: Settings) -> SearchPipeline:
    """Compose the ranking pipeline around a (resilient) provider."""
    spell = None
    if settings.enable_spell_correction:
        spell = SpellCorrector.from_events(load_fixture_events())
    return SearchPipeline(
        provider,
        spell=spell,
        expand=settings.enable_query_expansion,
        do_rerank=settings.enable_reranking,
        weights=RerankWeights(),
    )


def build_planner_and_answerer(
    settings: Settings,
) -> tuple[Planner, Answerer, list[object]]:
    """Build planner + answerer for the active mode."""
    closables: list[object] = []
    if settings.llm_is_real and settings.gemini_api_key:
        client = GeminiClient(settings.gemini_api_key, settings.gemini_model)
        closables.append(client)
        return GeminiPlanner(client), GeminiAnswerer(client), closables
    return MockPlanner(), MockAnswerer(), closables


def build_components(settings: Settings) -> Components:
    """Assemble the full agent for the active mode."""
    base, c1 = build_base_search_provider(settings)
    resilient = wrap_resilient(base, settings)
    pipeline = build_pipeline(resilient, settings)
    planner, answerer, c2 = build_planner_and_answerer(settings)
    sessions = SessionStore(ttl=settings.session_ttl)
    agent = RoverAgent(
        planner=planner, pipeline=pipeline, answerer=answerer, sessions=sessions
    )
    return Components(agent=agent, sessions=sessions, closables=[*c1, *c2])
