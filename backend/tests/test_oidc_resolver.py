"""Tests for the OIDC/JWT principal resolver (offline, self-signed keys)."""
from __future__ import annotations

import time

import pytest
from jose import jwt

from app.authz.oidc_resolver import OidcAuthError, OidcPrincipalResolver
from app.authz.policy import KeyBinding, PrincipalResolver

AUD = "rover"

# A small RSA keypair generated at import time (no network, no fixtures on disk).
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_priv_pem = _key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()
_pub_pem = _key.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
).decode()


def _token(claims: dict, exp_offset: int = 3600) -> str:
    body = {"aud": AUD, "exp": int(time.time()) + exp_offset, **claims}
    return jwt.encode(body, _priv_pem, algorithm="RS256")


def _resolver(**kw) -> OidcPrincipalResolver:
    return OidcPrincipalResolver(AUD, jwks=_pub_pem, **kw)


def test_valid_token_maps_groups_to_roles():
    r = _resolver()
    p = r.verify_token(_token({"sub": "u1", "groups": ["admin"]}))
    assert p.subject == "u1"
    assert "admin" in p.role_names()


def test_token_without_groups_defaults_to_visitor():
    r = _resolver()
    p = r.verify_token(_token({"sub": "u2"}))
    assert p.role_names() == ["visitor"]


def test_groups_mapping_translates_idp_group():
    r = _resolver(groups_mapping={"ops-team": "admin"})
    p = r.verify_token(_token({"sub": "u3", "groups": ["ops-team"]}))
    assert "admin" in p.role_names()


def test_unknown_group_falls_back_to_visitor():
    r = _resolver()
    p = r.verify_token(_token({"sub": "u4", "groups": ["nonsense-group"]}))
    assert p.role_names() == ["visitor"]


def test_tenant_claim_used():
    r = _resolver()
    p = r.verify_token(_token({"sub": "u5", "tenant": "acme", "groups": ["analyst"]}))
    assert p.tenant == "acme"


def test_expired_token_raises_401():
    r = _resolver(leeway=0)
    with pytest.raises(OidcAuthError):
        r.verify_token(_token({"sub": "u6"}, exp_offset=-120))


def test_invalid_token_raises_401():
    r = _resolver()
    with pytest.raises(OidcAuthError):
        r.verify_token("not.a.jwt")


def test_wrong_audience_raises_401():
    r = OidcPrincipalResolver("different-aud", jwks=_pub_pem)
    with pytest.raises(OidcAuthError):
        r.verify_token(_token({"sub": "u7"}))


def test_no_jwks_raises_401():
    r = OidcPrincipalResolver(AUD)  # no jwks
    with pytest.raises(OidcAuthError):
        r.verify_token(_token({"sub": "u8"}))


def test_jwks_argument_overrides():
    r = OidcPrincipalResolver(AUD)  # no instance jwks
    p = r.verify_token(_token({"sub": "u9", "groups": ["analyst"]}), jwks=_pub_pem)
    assert "analyst" in p.role_names()


def test_resolve_api_key_delegates_to_base():
    base = PrincipalResolver(
        [KeyBinding("k1", "svc", "default", ["admin"])], anonymous_role_names=["visitor"]
    )
    r = _resolver(base_resolver=base)
    assert r.resolve_api_key("k1").subject == "svc"
    assert r.resolve_api_key("bad").subject == "anonymous"


def test_resolve_api_key_no_base_returns_anonymous():
    r = _resolver()
    assert r.resolve_api_key("anything").subject == "anonymous"
