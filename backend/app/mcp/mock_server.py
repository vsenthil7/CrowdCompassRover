"""Local mock Elastic MCP server (JSON-RPC over HTTP).

Implements the same ``tools/call`` contract as the real Elastic MCP server for
``list_indices``, ``get_mappings`` and ``search`` against fixture data. Lets the REAL
provider code path (ElasticMCPClient + ElasticSearchProvider) be exercised end-to-end
locally before live Elastic credentials are available. Binds to localhost only.
"""
from __future__ import annotations

import json

from fastapi import FastAPI, Request

from app.core.embedding import embed
from app.data.fixtures import load_fixture_events
from app.models.domain import QueryPlan
from app.services.hybrid import hybrid_rank

app = FastAPI(title="Mock Elastic MCP Server")

_EVENTS = load_fixture_events()
for _ev in _EVENTS:
    _ev.embedding = embed(_ev.text_blob())


def _text_block(payload: object) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(payload)}]}


@app.post("/mcp")
async def mcp(request: Request) -> dict:  # pragma: no cover - exercised via live server
    body = await request.json()
    params = body.get("params", {})
    name = params.get("name")
    args = params.get("arguments", {})
    req_id = body.get("id")

    if name == "list_indices":
        result = _text_block([{"index": "cc-city-events"}])
    elif name == "get_mappings":
        result = _text_block({"properties": {"name": {"type": "text"}}})
    elif name == "search":
        # Reconstruct a minimal plan from the query body for ranking.
        plan = QueryPlan(
            original_query="",
            detected_language="en",
            normalized_query=str(args.get("query", {})),
            semantic_text="",
            top_k=int(args.get("query", {}).get("size", 5)),
        )
        ranked = hybrid_rank(plan, _EVENTS)
        hits = [
            {"_score": r.score, "_source": r.event.model_dump()} for r in ranked
        ]
        result = _text_block({"hits": {"hits": hits}})
    else:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"message": "unknown tool"}}

    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def main() -> None:  # pragma: no cover - CLI entry
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9100)


if __name__ == "__main__":  # pragma: no cover
    main()
