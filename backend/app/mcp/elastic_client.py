"""Client for the Elasticsearch MCP server (JSON-RPC over streamable HTTP).

This is the REAL integration. It is exercised when ``APP_MODE=real`` (or ``hybrid``) and
credentials are present. The transport is the MCP ``tools/call`` convention; tool names
match the shipped Elasticsearch MCP server: ``list_indices``, ``get_mappings``,
``search`` (query DSL) and ``esql``.

Until live credentials are available the class is unit-tested via a stubbed transport so
its request-construction and response-parsing logic is fully covered.
"""
from __future__ import annotations

import json
from typing import Any

import httpx


class ElasticMCPError(RuntimeError):
    """Raised when the MCP server returns an error envelope."""


class ElasticMCPClient:
    """Minimal JSON-RPC client for the Elastic MCP server."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            transport=transport,
            headers={
                "Authorization": f"ApiKey {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        self._id = 0

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Invoke an MCP tool and return its parsed result payload."""
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        resp = await self._client.post("/mcp", json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise ElasticMCPError(str(data["error"]))
        result = data.get("result", {})
        content = result.get("content", [])
        # MCP returns a list of content blocks; text blocks carry JSON strings.
        for block in content:
            if block.get("type") == "text":
                text = block.get("text", "")
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return text
        return result

    async def list_indices(self) -> Any:
        """Call the ``list_indices`` tool."""
        return await self._call_tool("list_indices", {})

    async def get_mappings(self, index: str) -> Any:
        """Call the ``get_mappings`` tool for an index."""
        return await self._call_tool("get_mappings", {"index": index})

    async def search(self, index: str, query: dict[str, Any]) -> Any:
        """Call the ``search`` tool with a query DSL body."""
        return await self._call_tool("search", {"index": index, "query": query})

    async def esql(self, query: str) -> Any:
        """Call the ``esql`` tool with an ES|QL statement."""
        return await self._call_tool("esql", {"query": query})
