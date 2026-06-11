"""Provider factory — selects mock vs real implementations from settings.

This is the single place where ``APP_MODE`` decides which concrete components are wired
into the agent. Switching MOCK -> REAL requires no code change anywhere else.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.agent.answerer import Answerer, MockAnswerer
from app.agent.gemini_client import GeminiClient
from app.agent.gemini_planner import GeminiAnswerer, GeminiPlanner
from app.agent.orchestrator import RoverAgent
from app.agent.planner import MockPlanner, Planner
from app.core.config import Settings
from app.mcp.elastic_client import ElasticMCPClient
from app.services.elastic_search import ElasticSearchProvider
from app.services.mock_search import MockSearchProvider
from app.services.search_provider import SearchProvider


@dataclass
class Components:
    """Constructed components plus any closables needing shutdown."""

    agent: RoverAgent
    closables: list[object]


def build_search_provider(settings: Settings) -> tuple[SearchProvider, list[object]]:
    """Build the search provider for the active mode."""
    closables: list[object] = []
    if settings.elastic_is_real and settings.elastic_mcp_url and settings.elastic_mcp_api_key:
        client = ElasticMCPClient(settings.elastic_mcp_url, settings.elastic_mcp_api_key)
        closables.append(client)
        return ElasticSearchProvider(client, settings.elastic_index), closables
    return MockSearchProvider(), closables


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
    search, c1 = build_search_provider(settings)
    planner, answerer, c2 = build_planner_and_answerer(settings)
    agent = RoverAgent(planner=planner, search=search, answerer=answerer)
    return Components(agent=agent, closables=[*c1, *c2])
