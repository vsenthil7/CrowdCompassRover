"""Tests for the ES query-DSL builder and the Elastic-MCP search provider."""
from __future__ import annotations

import json

import httpx
import pytest

from app.mcp.elastic_client import ElasticMCPClient, ElasticMCPError
from app.models.domain import GeoPoint, QueryPlan, SearchFilters, VenueCategory
from app.services.elastic_search import ElasticSearchProvider
from app.services.query_builder import build_query


def _plan(**kw) -> QueryPlan:
    base = dict(
        original_query="q",
        detected_language="en",
        normalized_query="stadium",
        semantic_text="stadium",
        filters=SearchFilters(),
        top_k=5,
    )
    base.update(kw)
    return QueryPlan(**base)


def test_build_query_basic_structure():
    body = build_query(_plan())
    assert body["size"] == 5
    assert "knn" in body
    assert body["query"]["bool"]["must"][0]["multi_match"]["query"] == "stadium"


def test_build_query_all_filters():
    f = SearchFilters(
        city="New York",
        category=VenueCategory.RESTAURANT,
        open_now=True,
        halal=True,
        vegetarian=False,
        wheelchair_accessible=True,
        near=GeoPoint(lat=40.0, lon=-74.0),
        max_distance_km=10.0,
    )
    body = build_query(_plan(filters=f))
    clauses = body["query"]["bool"]["filter"]
    assert {"term": {"city": "New York"}} in clauses
    assert {"term": {"category": "restaurant"}} in clauses
    assert {"term": {"open_now": True}} in clauses
    assert {"term": {"halal": True}} in clauses
    assert {"term": {"vegetarian": False}} in clauses
    assert {"term": {"wheelchair_accessible": True}} in clauses
    assert any("geo_distance" in c for c in clauses)


def test_build_query_near_without_distance_no_geo():
    f = SearchFilters(near=GeoPoint(lat=1, lon=2))
    body = build_query(_plan(filters=f))
    assert not any("geo_distance" in c for c in body["query"]["bool"]["filter"])


def _mock_transport(handler):
    return httpx.MockTransport(handler)


async def test_elastic_client_call_tool_parses_text_json():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": json.dumps([{"index": "i"}])}]},
        }
        return httpx.Response(200, json=payload)

    client = ElasticMCPClient("http://mcp", "key", transport=_mock_transport(handler))
    res = await client.list_indices()
    assert res == [{"index": "i"}]
    await client.aclose()


async def test_elastic_client_non_json_text_returned_raw():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"content": [{"type": "text", "text": "plain text"}]},
        }
        return httpx.Response(200, json=payload)

    client = ElasticMCPClient("http://mcp", "key", transport=_mock_transport(handler))
    res = await client.get_mappings("i")
    assert res == "plain text"
    await client.aclose()


async def test_elastic_client_no_text_block_returns_result():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = {"jsonrpc": "2.0", "id": 1, "result": {"other": 1}}
        return httpx.Response(200, json=payload)

    client = ElasticMCPClient("http://mcp", "key", transport=_mock_transport(handler))
    res = await client.esql("FROM x")
    assert res == {"other": 1}
    await client.aclose()


async def test_elastic_client_error_envelope_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "error": {"message": "boom"}})

    client = ElasticMCPClient("http://mcp", "key", transport=_mock_transport(handler))
    with pytest.raises(ElasticMCPError):
        await client.list_indices()
    await client.aclose()


async def test_elastic_client_search_passes_body():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "{}"}]}},
        )

    client = ElasticMCPClient("http://mcp", "key", transport=_mock_transport(handler))
    await client.search("idx", {"size": 3})
    assert captured["body"]["params"]["arguments"]["index"] == "idx"
    await client.aclose()


# --- ElasticSearchProvider ---


class _StubClient:
    def __init__(self, list_res=None, map_res=None, search_res=None):
        self._list = list_res
        self._map = map_res
        self._search = search_res

    async def list_indices(self):
        return self._list

    async def get_mappings(self, index):
        return self._map

    async def search(self, index, query):
        return self._search


async def test_provider_list_indices_list_of_dicts():
    p = ElasticSearchProvider(_StubClient(list_res=[{"index": "a"}, {"index": "b"}]), "a")
    assert await p.list_indices() == ["a", "b"]


async def test_provider_list_indices_list_of_strings():
    p = ElasticSearchProvider(_StubClient(list_res=["a", "b"]), "a")
    assert await p.list_indices() == ["a", "b"]


async def test_provider_list_indices_dict_form():
    p = ElasticSearchProvider(_StubClient(list_res={"indices": ["x"]}), "x")
    assert await p.list_indices() == ["x"]


async def test_provider_list_indices_fallback():
    p = ElasticSearchProvider(_StubClient(list_res=None), "fallback")
    assert await p.list_indices() == ["fallback"]


async def test_provider_get_mappings_dict():
    p = ElasticSearchProvider(_StubClient(map_res={"properties": {}}), "a")
    assert await p.get_mappings("a") == {"properties": {}}


async def test_provider_get_mappings_non_dict_wrapped():
    p = ElasticSearchProvider(_StubClient(map_res="raw"), "a")
    assert await p.get_mappings("a") == {"raw": "raw"}


async def test_provider_search_parses_hits():
    hit_source = {
        "id": "x",
        "name": "Test Stadium",
        "category": "stadium",
        "city": "New York",
        "description": "d",
        "location": {"lat": 40.0, "lon": -74.0},
        "open_now": True,
    }
    raw = {"hits": {"hits": [{"_score": 1.5, "_source": hit_source}]}}
    p = ElasticSearchProvider(_StubClient(search_res=raw), "a")
    plan = _plan(filters=SearchFilters(near=GeoPoint(lat=40.0, lon=-74.0)))
    results = await p.search(plan)
    assert len(results) == 1
    assert results[0].event.name == "Test Stadium"
    assert results[0].distance_km is not None


async def test_provider_search_skips_malformed_doc():
    raw = {"hits": {"hits": [{"_score": 1.0, "_source": {"bad": "doc"}}]}}
    p = ElasticSearchProvider(_StubClient(search_res=raw), "a")
    results = await p.search(_plan())
    assert results == []


async def test_provider_search_non_dict_raw():
    p = ElasticSearchProvider(_StubClient(search_res="oops"), "a")
    results = await p.search(_plan())
    assert results == []
