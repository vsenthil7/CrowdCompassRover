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


# --- P2.S1: put_mapping / delete_index / bulk_index / count ---


def _capture_transport(captured: dict, result_payload):
    """A transport that records the outgoing MCP call and returns result_payload."""
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        captured["name"] = body["params"]["name"]
        captured["arguments"] = body["params"]["arguments"]
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body["id"],
                "result": {"content": [{"type": "text", "text": json.dumps(result_payload)}]},
            },
        )

    return httpx.MockTransport(handler)


async def test_put_mapping_calls_create_index():
    captured: dict = {}
    client = ElasticMCPClient(
        "http://mcp", "key", transport=_capture_transport(captured, {"acknowledged": True})
    )
    res = await client.put_mapping("cc-city-events", {"properties": {"name": {"type": "text"}}})
    assert res == {"acknowledged": True}
    assert captured["name"] == "create_index"
    assert captured["arguments"]["index"] == "cc-city-events"
    assert captured["arguments"]["mappings"] == {"properties": {"name": {"type": "text"}}}
    await client.aclose()


async def test_delete_index_calls_delete_tool():
    captured: dict = {}
    client = ElasticMCPClient(
        "http://mcp", "key", transport=_capture_transport(captured, {"acknowledged": True})
    )
    await client.delete_index("cc-city-events")
    assert captured["name"] == "delete_index"
    assert captured["arguments"] == {"index": "cc-city-events"}
    await client.aclose()


async def test_bulk_index_emits_action_source_pairs():
    captured: dict = {}
    client = ElasticMCPClient(
        "http://mcp", "key", transport=_capture_transport(captured, {"errors": False, "items": []})
    )
    docs = [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}]
    res = await client.bulk_index("cc-city-events", docs)
    assert res == {"errors": False, "items": []}
    ops = captured["arguments"]["operations"]
    # action line + source line per doc => 4 entries
    assert len(ops) == 4
    assert ops[0] == {"index": {"_index": "cc-city-events", "_id": "a"}}
    assert ops[1] == {"id": "a", "name": "A"}
    assert ops[2] == {"index": {"_index": "cc-city-events", "_id": "b"}}
    await client.aclose()


async def test_bulk_index_missing_id_defaults_empty():
    captured: dict = {}
    client = ElasticMCPClient(
        "http://mcp", "key", transport=_capture_transport(captured, {"errors": False})
    )
    await client.bulk_index("idx", [{"name": "no-id"}])
    ops = captured["arguments"]["operations"]
    assert ops[0] == {"index": {"_index": "idx", "_id": ""}}
    await client.aclose()


async def test_count_returns_int():
    captured: dict = {}
    client = ElasticMCPClient("http://mcp", "key", transport=_capture_transport(captured, {"count": 42}))
    n = await client.count("cc-city-events")
    assert n == 42
    assert captured["name"] == "count"
    await client.aclose()


async def test_count_non_dict_result_returns_zero():
    captured: dict = {}
    client = ElasticMCPClient("http://mcp", "key", transport=_capture_transport(captured, [1, 2, 3]))
    n = await client.count("cc-city-events")
    assert n == 0
    await client.aclose()


# --- P2.S3: RRF ranking + open_now boost + tunable weights ---


def test_rrf_rank_present():
    body = build_query(_plan())
    assert "rank" in body
    assert body["rank"]["rrf"]["window_size"] == 100
    assert body["rank"]["rrf"]["rank_constant"] == 60


def test_open_now_boost_in_should():
    body = build_query(_plan(filters=SearchFilters(open_now=True)))
    should = body["query"]["bool"].get("should", [])
    assert any("open_now" in str(c) for c in should)
    assert body["query"]["bool"]["minimum_should_match"] == 0


def test_no_open_now_no_should():
    body = build_query(_plan())
    assert "should" not in body["query"]["bool"]


def test_weights_passed_to_clauses():
    body = build_query(_plan(), keyword_weight=0.3, vector_weight=0.7)
    assert body["knn"]["boost"] == 0.7
    assert body["query"]["bool"]["must"][0]["multi_match"]["boost"] == 0.3


def test_knn_k_capped_by_window():
    body = build_query(_plan(top_k=40), rrf_window_size=50)
    assert body["knn"]["k"] == 50  # min(top_k*2=80, window=50)


def test_knn_k_uses_double_top_k_when_below_window():
    body = build_query(_plan(top_k=5), rrf_window_size=100)
    assert body["knn"]["k"] == 10  # min(10, 100)


def test_no_filter_clauses_when_empty():
    body = build_query(_plan())
    assert body["query"]["bool"]["filter"] == []
