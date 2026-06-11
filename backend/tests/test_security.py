"""Tests for auth, rate limiting, and security middleware."""
from __future__ import annotations

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.security.auth import ApiKeyAuthenticator, parse_keys
from app.security.middleware import SecurityMiddleware
from app.security.rate_limit import TokenBucketRateLimiter


# --- auth ---


def test_auth_disabled_when_no_keys():
    auth = ApiKeyAuthenticator(set())
    assert auth.enabled is False
    assert auth.is_valid(None) is True
    assert auth.is_valid("anything") is True


def test_auth_enabled_validates():
    auth = ApiKeyAuthenticator({"secret1", "secret2"})
    assert auth.enabled is True
    assert auth.is_valid("secret1") is True
    assert auth.is_valid("wrong") is False
    assert auth.is_valid(None) is False


def test_auth_ignores_empty_keys():
    auth = ApiKeyAuthenticator({"", "k"})
    assert auth.is_valid("k") is True


def test_parse_keys():
    assert parse_keys("a, b ,, c") == {"a", "b", "c"}
    assert parse_keys("") == set()


# --- rate limiter ---


def test_rate_limiter_allows_within_capacity():
    clock = {"t": 0.0}
    rl = TokenBucketRateLimiter(rate=1.0, capacity=3.0, clock=lambda: clock["t"])
    assert rl.allow("k")
    assert rl.allow("k")
    assert rl.allow("k")
    assert not rl.allow("k")


def test_rate_limiter_refills():
    clock = {"t": 0.0}
    rl = TokenBucketRateLimiter(rate=1.0, capacity=1.0, clock=lambda: clock["t"])
    assert rl.allow("k")
    assert not rl.allow("k")
    clock["t"] = 1.0
    assert rl.allow("k")


def test_rate_limiter_remaining():
    clock = {"t": 0.0}
    rl = TokenBucketRateLimiter(rate=1.0, capacity=5.0, clock=lambda: clock["t"])
    assert rl.remaining("new") == 5.0
    rl.allow("new")
    assert rl.remaining("new") == 4.0


def test_rate_limiter_separate_keys():
    rl = TokenBucketRateLimiter(rate=0.0, capacity=1.0)
    assert rl.allow("a")
    assert rl.allow("b")
    assert not rl.allow("a")


# --- middleware integration against a minimal app ---


def _make_app(authenticator: ApiKeyAuthenticator, limiter: TokenBucketRateLimiter) -> Starlette:
    async def health(_request):
        return JSONResponse({"ok": True})

    async def protected(_request):
        return JSONResponse({"data": "secret"})

    app = Starlette(
        routes=[
            Route("/api/health", health),
            Route("/api/search", protected, methods=["POST"]),
        ]
    )
    app.add_middleware(SecurityMiddleware, authenticator=authenticator, limiter=limiter)
    return app


async def _client(app):
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_public_path_bypasses_auth():
    app = _make_app(ApiKeyAuthenticator({"k"}), TokenBucketRateLimiter())
    async with await _client(app) as c:
        r = await c.get("/api/health")
        assert r.status_code == 200


async def test_rejects_missing_key():
    app = _make_app(ApiKeyAuthenticator({"k"}), TokenBucketRateLimiter())
    async with await _client(app) as c:
        r = await c.post("/api/search", json={})
        assert r.status_code == 401
        assert r.headers["content-type"].startswith("application/problem+json")


async def test_accepts_valid_key():
    app = _make_app(ApiKeyAuthenticator({"k"}), TokenBucketRateLimiter())
    async with await _client(app) as c:
        r = await c.post("/api/search", json={}, headers={"X-API-Key": "k"})
        assert r.status_code == 200


async def test_rate_limit_triggers():
    app = _make_app(ApiKeyAuthenticator(set()), TokenBucketRateLimiter(rate=0.0, capacity=1.0))
    async with await _client(app) as c:
        assert (await c.post("/api/search", json={})).status_code == 200
        assert (await c.post("/api/search", json={})).status_code == 429


async def test_non_http_scope_passes_through():
    # Lifespan events use a non-http scope; middleware must not interfere.
    app = _make_app(ApiKeyAuthenticator({"k"}), TokenBucketRateLimiter())
    from asgi_lifespan import LifespanManager

    async with LifespanManager(app):
        pass
