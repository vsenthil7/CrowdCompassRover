"""Tests for the partner data connector framework (offline, mock transport)."""
from __future__ import annotations

import json

import httpx

from app.connectors.base import ConnectorSpec, ConnectorStatus
from app.connectors.registry import ConnectorRegistry
from app.connectors.rest_connector import RestJsonConnector, map_record
from app.models.domain import VenueCategory


def test_map_record_full():
    raw = {"id": "x1", "title": "Cafe", "city": "Madrid", "category": "restaurant",
           "location": {"lat": 40.0, "lon": -3.0}}
    ev = map_record(raw, {"title": "name"}, "c1")
    assert ev is not None
    assert ev.name == "Cafe"
    assert ev.category is VenueCategory.RESTAURANT
    assert ev.city == "Madrid"


def test_map_record_unknown_category_defaults_info_kiosk():
    ev = map_record({"id": "x", "name": "N", "category": "spaceship"}, {}, "c1")
    assert ev.category is VenueCategory.INFO_KIOSK


def test_map_record_defaults_for_missing_fields():
    ev = map_record({}, {}, "c1")
    assert ev is not None
    assert ev.name == "Unknown"
    assert ev.city == "unknown"


def test_map_record_malformed_returns_none():
    # name is forced to a type that fails validation.
    ev = map_record({"id": "x", "name": {"bad": "type"}}, {}, "c1")
    assert ev is None


def _paged_transport(pages):
    """MockTransport returning successive JSON page bodies keyed by the page param."""
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        body = pages[page - 1] if page - 1 < len(pages) else {"results": []}
        return httpx.Response(200, json=body)
    return httpx.MockTransport(handler)


async def test_rest_connector_paginates():
    spec = ConnectorSpec("c1", "rest_json", "http://x/api", per_page=2, field_map={"title": "name"})
    pages = [
        {"results": [{"id": "1", "title": "A", "city": "M"}, {"id": "2", "title": "B", "city": "M"}]},
        {"results": [{"id": "3", "title": "C", "city": "M"}]},  # short page -> stop
    ]
    conn = RestJsonConnector(spec, transport=_paged_transport(pages))
    events, errors = await conn.fetch_all()
    assert [e.id for e in events] == ["1", "2", "3"]
    assert errors == []


async def test_rest_connector_auth_header_and_http_error():
    spec = ConnectorSpec("c2", "rest_json", "http://x/api", auth_header="Bearer t")
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer t"
        return httpx.Response(500)
    conn = RestJsonConnector(spec, transport=httpx.MockTransport(handler))
    events, errors = await conn.fetch_all()
    assert events == []
    assert len(errors) == 1


async def test_rest_connector_empty_results_stops():
    spec = ConnectorSpec("c3", "rest_json", "http://x/api")
    conn = RestJsonConnector(spec, transport=_paged_transport([{"results": []}]))
    events, errors = await conn.fetch_all()
    assert events == [] and errors == []


async def test_rest_connector_list_body():
    spec = ConnectorSpec("c4", "rest_json", "http://x/api", per_page=5)
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        return httpx.Response(200, json=[{"id": "1", "name": "A", "city": "M"}] if page == 1 else [])
    conn = RestJsonConnector(spec, transport=httpx.MockTransport(handler))
    events, _ = await conn.fetch_all()
    assert len(events) == 1


# --- registry ---

def test_registry_crud_and_status():
    reg = ConnectorRegistry()
    spec = ConnectorSpec("c1", "rest_json", "http://x", tenant="acme")
    reg.register(spec)
    assert reg.get("c1") is spec
    assert reg.for_tenant("acme") == [spec]
    assert reg.status("c1").record_count == 0
    reg.set_status(ConnectorStatus("c1", record_count=5, healthy=True))
    assert reg.status("c1").record_count == 5
    assert reg.remove("c1") is True
    assert reg.remove("c1") is False
    assert reg.get("c1") is None
    assert reg.status("c1") is None
