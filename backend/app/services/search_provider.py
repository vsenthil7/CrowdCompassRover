"""Search provider abstraction.

Both the in-memory mock and the live Elastic-MCP-backed implementation satisfy this
protocol, so the agent and API layers are agnostic to which is active.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.models.domain import QueryPlan, ScoredEvent


@runtime_checkable
class SearchProvider(Protocol):
    """Hybrid search over city/event data."""

    async def list_indices(self) -> list[str]:
        """Return available index names (Elastic MCP ``list_indices``)."""
        ...

    async def get_mappings(self, index: str) -> dict:
        """Return field mappings for an index (Elastic MCP ``get_mappings``)."""
        ...

    async def search(self, plan: QueryPlan) -> list[ScoredEvent]:
        """Run a hybrid search for the given plan and return ranked hits."""
        ...
