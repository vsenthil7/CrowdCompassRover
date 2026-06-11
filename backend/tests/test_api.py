"""Integration tests for the FastAPI routes and dependency lifecycle."""
from __future__ import annotations

import httpx
import pytest
from asgi_lifespan import LifespanManager

from app.api import deps
from app.main import create_app


@pytest.fixture
async def client():
    # Reset module-level component cache for isolation.
    deps._components = None
    app = create_app()
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    deps._components = None


async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mode"] == "mock"


async def test_indices(client):
    r = await client.get("/api/indices")
    assert r.status_code == 200
    assert "cc-city-events" in r.json()["indices"]


async def test_search_endpoint(client):
    r = await client.post(
        "/api/search",
        json={"query": "halal food open now", "user_location": {"lat": 40.81, "lon": -74.07}, "top_k": 3},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["plan"]["filters"]["halal"] is True
    assert len(body["results"]) <= 3


async def test_search_validation_error(client):
    r = await client.post("/api/search", json={"query": ""})
    assert r.status_code == 422


async def test_chat_endpoint(client):
    r = await client.post("/api/chat", json={"query": "where is the stadium"})
    assert r.status_code == 200
    body = r.json()
    assert body["language"] == "en"
    assert "answer" in body


async def test_chat_stream_endpoint(client):
    r = await client.post("/api/chat/stream", json={"query": "halal food open now"})
    assert r.status_code == 200
    text = r.text
    assert "event: language" in text
    assert "event: token" in text
    assert "event: done" in text


async def test_get_agent_lazy_init():
    # When components not initialized, get_agent should build them on demand.
    deps._components = None
    agent = deps.get_agent()
    assert agent is not None
    deps._components = None


async def test_shutdown_when_uninitialized_is_safe():
    deps._components = None
    await deps.shutdown_components()  # should not raise


async def test_shutdown_closes_closables():
    closed = {"v": False}

    class _C:
        async def aclose(self):
            closed["v"] = True

    from app.core.providers import Components

    deps._components = Components(agent=object(), closables=[_C(), object()])
    await deps.shutdown_components()
    assert closed["v"] is True
    assert deps._components is None
