"""Tests for multi-tenancy and API versioning."""
from __future__ import annotations

from datetime import date

import pytest

from app.tenancy.context import (
    InvalidTenantError,
    TenantContext,
    TenantResolver,
    UnknownTenantError,
    get_current_tenant,
    reset_current_tenant,
    set_current_tenant,
    validate_tenant_id,
)
from app.versioning.registry import ApiVersion, VersionRegistry, default_registry


# --- tenancy ---


def test_validate_tenant_id_normalises():
    assert validate_tenant_id("  Acme-1 ") == "acme-1"


def test_validate_tenant_id_rejects_bad():
    for bad in ["", "-bad", "a/b", "x" * 70, "UPPER!"]:
        with pytest.raises(InvalidTenantError):
            validate_tenant_id(bad)


def test_tenant_context_scoped_key():
    ctx = TenantContext(tenant_id="acme")
    assert ctx.scoped_key("events") == "acme::events"


def test_resolver_prefers_principal():
    resolver = TenantResolver()
    ctx = resolver.resolve(principal_tenant="acme", header_tenant="other")
    assert ctx.tenant_id == "acme"


def test_resolver_header_fallback_then_default():
    resolver = TenantResolver(default="base")
    assert resolver.resolve(principal_tenant=None, header_tenant="hh").tenant_id == "hh"
    assert resolver.resolve(principal_tenant=None, header_tenant=None).tenant_id == "base"


def test_resolver_allowlist():
    resolver = TenantResolver(known={"acme", "globex"})
    assert resolver.resolve(principal_tenant="acme", header_tenant=None).tenant_id == "acme"
    with pytest.raises(UnknownTenantError):
        resolver.resolve(principal_tenant="evil", header_tenant=None)


def test_resolver_register():
    resolver = TenantResolver(known={"acme"})
    resolver.register("globex")
    assert resolver.is_known("globex")


def test_resolver_register_creates_allowlist():
    resolver = TenantResolver()  # no allow-list (all allowed)
    assert resolver.is_known("anything") is True
    resolver.register("acme")
    assert resolver.is_known("acme") is True
    assert resolver.is_known("other") is False  # now an allow-list exists


def test_tenant_context_var():
    assert get_current_tenant() is None
    token = set_current_tenant(TenantContext("acme"))
    assert get_current_tenant().tenant_id == "acme"
    reset_current_tenant(token)
    assert get_current_tenant() is None


# --- versioning ---


def test_default_registry():
    reg = default_registry()
    assert reg.current == "v1"
    assert reg.is_supported("v1")
    assert reg.supported_names() == ["v1"]


def test_registry_register_and_current():
    reg = VersionRegistry()
    reg.register(ApiVersion("v1", date(2026, 1, 1)))
    reg.register(ApiVersion("v2", date(2026, 6, 1)), make_current=True)
    assert reg.current == "v2"
    assert set(reg.supported_names()) == {"v1", "v2"}


def test_registry_deprecation_headers():
    reg = VersionRegistry()
    reg.register(
        ApiVersion("v1", date(2026, 1, 1), deprecated=True, sunset=date(2026, 12, 31))
    )
    reg.register(ApiVersion("v2", date(2026, 6, 1)), make_current=True)
    headers = reg.deprecation_headers("v1")
    assert headers["Deprecation"] == "true"
    assert headers["Sunset"] == "2026-12-31"
    assert reg.deprecation_headers("v2") == {}


def test_registry_deprecated_without_sunset():
    reg = VersionRegistry()
    reg.register(ApiVersion("v0", date(2025, 1, 1), deprecated=True))
    headers = reg.deprecation_headers("v0")
    assert headers == {"Deprecation": "true"}


def test_registry_unknown_version_headers():
    reg = default_registry()
    assert reg.deprecation_headers("v9") == {}
    assert reg.get("v9") is None
