"""RBAC enforcement tests at the HTTP route layer.

Proves the policy engine is actually wired into routes (not just built): elevated
routes reject callers without the permission (403 forbidden), accept an admin key,
and the public baseline keeps search/chat/route open zero-config in mock mode.
"""
from __future__ import annotations

import httpx
import pytest
from asgi_lifespan import LifespanManager

from app.api import deps
from app.core import config as config_module
from app.main import create_app

ADMIN_KEY = "test-admin-key"

# Routes that must reject a permissionless caller, with the verb + sample body.
ELEVATED = [
    ("get", "/api/analytics", None),
    ("get", "/api/traces", None),
    ("get", "/api/admin/status", None),
    ("post", "/api/admin/cache/flush", None),
    ("post", "/api/admin/reindex", None),
    ("post", "/api/admin/retention/sweep", None),
    ("post", "/api/admin/outbox/relay", None),
    ("get", "/api/gdpr/export/subj-1", None),
    ("delete", "/api/gdpr/subj-1", None),
    ("post", "/api/webhooks", {"tenant": "default", "url": "https://example.com/h", "secret": "secret-123", "events": ["search.performed"]}),
]


@pytest.fixture
async def anon_app():
    """App with NO api keys configured; caller sends no key -> visitor baseline only."""
    monkey = pytest.MonkeyPatch()
    monkey.setenv("API_KEYS", "")
    config_module.get_settings.cache_clear()
    deps._components = None
    app = create_app()
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    deps._components = None
    config_module.get_settings.cache_clear()
    monkey.undo()


@pytest.fixture
async def keyed_app():
    """App with an admin key configured; client sends it on every request."""
    monkey = pytest.MonkeyPatch()
    monkey.setenv("API_KEYS", ADMIN_KEY)
    config_module.get_settings.cache_clear()
    deps._components = None
    app = create_app()
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test", headers={"X-API-Key": ADMIN_KEY}
        ) as c:
            yield c
    deps._components = None
    config_module.get_settings.cache_clear()
    monkey.undo()


@pytest.mark.parametrize("verb,path,body", ELEVATED)
async def test_elevated_route_forbidden_for_anonymous(anon_app, verb, path, body):
    r = await getattr(anon_app, verb)(path, json=body) if body else await getattr(anon_app, verb)(path)
    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"


@pytest.mark.parametrize("verb,path,body", ELEVATED)
async def test_elevated_route_allowed_for_admin(keyed_app, verb, path, body):
    r = await getattr(keyed_app, verb)(path, json=body) if body else await getattr(keyed_app, verb)(path)
    assert r.status_code != 403


async def test_public_baseline_allows_search_without_key(anon_app):
    r = await anon_app.post("/api/search", json={"query": "halal food open now"})
    assert r.status_code == 200


async def test_public_baseline_allows_chat_without_key(anon_app):
    r = await anon_app.post("/api/chat", json={"query": "where can I eat"})
    assert r.status_code == 200


async def test_wrong_key_is_treated_as_anonymous(anon_app):
    # A bogus key resolves to the visitor baseline, so search works but analytics is 403.
    r_search = await anon_app.post("/api/search", json={"query": "x"}, headers={"X-API-Key": "bogus"})
    assert r_search.status_code == 200
    r_an = await anon_app.get("/api/analytics", headers={"X-API-Key": "bogus"})
    assert r_an.status_code == 403


async def test_baseline_off_locks_down_search(monkeypatch):
    """With rbac_public_baseline disabled, even search requires a permission."""
    monkeypatch.setenv("API_KEYS", "")
    monkeypatch.setenv("RBAC_PUBLIC_BASELINE", "false")
    config_module.get_settings.cache_clear()
    deps._components = None
    app = create_app()
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/search", json={"query": "x"})
    deps._components = None
    config_module.get_settings.cache_clear()
    assert r.status_code == 403
