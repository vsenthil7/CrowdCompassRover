"""Real search provider backed by the Elastic MCP server.

Activated in ``APP_MODE=real``/``hybrid`` when credentials are present. Builds the hybrid
query DSL from the plan, calls the MCP ``search`` tool, and parses ES hits back into
domain :class:`ScoredEvent` objects.
"""
from __future__ import annotations

from typing import Any

from app.core.geo import haversine_km
from app.mcp.elastic_client import ElasticMCPClient
from app.models.domain import CityEvent, QueryPlan, ScoredEvent
from app.services.query_builder import build_query


class ElasticSearchProvider:
    """SearchProvider implementation over the Elastic MCP server."""

    def __init__(self, client: ElasticMCPClient, index: str) -> None:
        self._client = client
        self._index = index

    async def list_indices(self) -> list[str]:
        """Return index names reported by the MCP server."""
        result = await self._client.list_indices()
        if isinstance(result, list):
            return [
                item.get("index", item) if isinstance(item, dict) else item
                for item in result
            ]
        if isinstance(result, dict) and "indices" in result:
            return list(result["indices"])
        return [self._index]

    async def get_mappings(self, index: str) -> dict:
        """Return the mapping reported by the MCP server."""
        result = await self._client.get_mappings(index)
        if isinstance(result, dict):
            return result
        return {"raw": result}

    async def search(self, plan: QueryPlan) -> list[ScoredEvent]:
        """Run the hybrid query via the MCP search tool and parse hits."""
        body = build_query(plan)
        raw = await self._client.search(self._index, body)
        return self._parse_hits(raw, plan)

    def _parse_hits(self, raw: Any, plan: QueryPlan) -> list[ScoredEvent]:
        hits = []
        if isinstance(raw, dict):
            hits = raw.get("hits", {}).get("hits", [])
        scored: list[ScoredEvent] = []
        for hit in hits:
            source = hit.get("_source", {})
            try:
                event = CityEvent(**source)
            except Exception:  # noqa: BLE001 - skip malformed docs defensively
                continue
            distance = None
            if plan.filters.near is not None:
                distance = haversine_km(plan.filters.near, event.location)
            scored.append(
                ScoredEvent(
                    event=event,
                    score=float(hit.get("_score", 0.0)),
                    distance_km=distance,
                )
            )
        return scored
