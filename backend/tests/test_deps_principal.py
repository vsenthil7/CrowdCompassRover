"""Tests for get_principal and get_policy FastAPI dependencies."""
from __future__ import annotations

from unittest.mock import MagicMock

from starlette.requests import Request

from app.api import deps
from app.authz.policy import KeyBinding, PolicyEngine, PrincipalResolver


def _make_request(api_key: str = "") -> Request:
    scope = {
        "type": "http",
        "headers": [(b"x-api-key", api_key.encode())] if api_key else [],
    }
    return Request(scope)


def _components_with_admin_key(monkeypatch):
    resolver = PrincipalResolver(
        [KeyBinding(api_key="admin-key", subject="admin", tenant="default", role_names=["admin"])],
        anonymous_role_names=["visitor"],
    )
    policy = PolicyEngine()
    mock_comps = MagicMock()
    mock_comps.resolver = resolver
    mock_comps.policy = policy
    monkeypatch.setattr(deps, "_components", mock_comps)
    return mock_comps


def test_get_principal_with_valid_key(monkeypatch):
    _components_with_admin_key(monkeypatch)
    p = deps.get_principal(_make_request("admin-key"))
    assert p.subject == "admin"
    assert "admin" in p.role_names()


def test_get_principal_no_key_returns_baseline(monkeypatch):
    _components_with_admin_key(monkeypatch)
    p = deps.get_principal(_make_request(""))
    assert p.subject == "anonymous"
    assert "visitor" in p.role_names()


def test_get_principal_wrong_key_returns_baseline(monkeypatch):
    _components_with_admin_key(monkeypatch)
    p = deps.get_principal(_make_request("wrong-key"))
    assert p.subject == "anonymous"


def test_get_policy_returns_policy_engine(monkeypatch):
    _components_with_admin_key(monkeypatch)
    assert isinstance(deps.get_policy(), PolicyEngine)
