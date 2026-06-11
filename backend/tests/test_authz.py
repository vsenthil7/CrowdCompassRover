"""Tests for RBAC, policy engine, and principal resolution."""
from __future__ import annotations

import pytest

from app.authz.policy import (
    AuthorizationError,
    KeyBinding,
    PolicyEngine,
    PrincipalResolver,
)
from app.authz.rbac import (
    ANONYMOUS,
    BUILTIN_ROLES,
    ROLE_ADMIN,
    ROLE_ANALYST,
    ROLE_VISITOR,
    Permission,
    Principal,
    Role,
)


def test_role_grants():
    assert ROLE_VISITOR.grants(Permission.SEARCH) is True
    assert ROLE_VISITOR.grants(Permission.ADMIN_CACHE) is False


def test_role_hierarchy():
    assert ROLE_VISITOR.permissions <= ROLE_ANALYST.permissions
    assert ROLE_ANALYST.permissions <= ROLE_ADMIN.permissions
    assert Permission.PURGE_DATA in ROLE_ADMIN.permissions


def test_principal_permissions_union():
    p = Principal("u", "t", roles=[ROLE_VISITOR, ROLE_ANALYST])
    perms = p.permissions()
    assert Permission.VIEW_ANALYTICS in perms
    assert Permission.SEARCH in perms
    assert p.role_names() == ["visitor", "analyst"]


def test_anonymous_has_no_permissions():
    assert ANONYMOUS.permissions() == set()


def test_builtin_roles_registry():
    assert set(BUILTIN_ROLES) == {"visitor", "analyst", "admin"}


def test_resolver_unknown_key_anonymous():
    resolver = PrincipalResolver()
    assert resolver.resolve("nope").subject == "anonymous"
    assert resolver.resolve(None).subject == "anonymous"


def test_resolver_known_key():
    resolver = PrincipalResolver(
        [KeyBinding(api_key="k1", subject="alice", tenant="acme", role_names=["analyst"])]
    )
    principal = resolver.resolve("k1")
    assert principal.subject == "alice"
    assert principal.tenant == "acme"
    assert "analyst" in principal.role_names()


def test_resolver_register_and_unknown_role_ignored():
    resolver = PrincipalResolver()
    resolver.register(
        KeyBinding(api_key="k", subject="bob", tenant="t", role_names=["analyst", "ghost"])
    )
    principal = resolver.resolve("k")
    assert principal.role_names() == ["analyst"]  # ghost role dropped


def test_policy_allows_and_require():
    engine = PolicyEngine()
    admin = Principal("a", "t", roles=[ROLE_ADMIN])
    assert engine.allows(admin, Permission.ADMIN_REINDEX) is True
    engine.require(admin, Permission.ADMIN_REINDEX)  # no raise


def test_policy_require_denied():
    engine = PolicyEngine()
    visitor = Principal("v", "t", roles=[ROLE_VISITOR])
    assert engine.allows(visitor, Permission.PURGE_DATA) is False
    with pytest.raises(AuthorizationError) as exc:
        engine.require(visitor, Permission.PURGE_DATA)
    assert exc.value.status_code == 403
    assert exc.value.code == "forbidden"


def test_custom_role():
    role = Role("custom", frozenset({Permission.SEARCH}))
    assert role.grants(Permission.SEARCH)
    assert not role.grants(Permission.CHAT)
