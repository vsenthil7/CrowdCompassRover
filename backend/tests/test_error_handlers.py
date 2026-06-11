"""Tests for the problem+json exception handlers."""
from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from app.errors.exceptions import RoverError, UpstreamUnavailableError
from app.errors.handlers import rover_error_handler, unhandled_error_handler


@pytest.fixture
async def client():
    app = FastAPI()
    app.add_exception_handler(RoverError, rover_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)

    @app.get("/rover")
    async def rover_route():
        raise UpstreamUnavailableError("backend down")

    @app.get("/boom")
    async def boom_route():
        raise RuntimeError("unexpected")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_rover_error_rendered_as_problem(client):
    r = await client.get("/rover")
    assert r.status_code == 503
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["code"] == "upstream_unavailable"
    assert body["instance"] == "/rover"
    assert body["detail"] == "backend down"


async def test_unhandled_error_rendered_as_problem(client):
    r = await client.get("/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["code"] == "internal_error"
    assert body["instance"] == "/boom"
