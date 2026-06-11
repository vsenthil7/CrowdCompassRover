"""OIDC / JWT principal resolution.

Validates Bearer JWTs against a JWKS key set and maps the token's ``groups`` claim onto the
built-in roles. The JWKS can be injected (for tests / preloaded keys) or fetched from the
configured ``jwks_uri`` at runtime; verification itself is pure and offline-testable.
API-key auth still works alongside this for service accounts.
"""
from __future__ import annotations

from typing import Any

from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from app.authz.rbac import ANONYMOUS, BUILTIN_ROLES, Principal, Role
from app.errors.exceptions import RoverError


class OidcAuthError(RoverError):
    """Raised when a Bearer token is missing/expired/invalid."""

    status_code = 401
    code = "unauthorized"
    title = "Unauthorized"


class OidcPrincipalResolver:
    """Resolves OIDC Bearer JWTs to Principals; maps ``groups`` -> roles."""

    def __init__(
        self,
        audience: str,
        *,
        jwks: dict[str, Any] | None = None,
        groups_mapping: dict[str, str] | None = None,
        leeway: int = 30,
        base_resolver: Any | None = None,
    ) -> None:
        self._audience = audience
        self._jwks = jwks
        self._groups_mapping = groups_mapping or {}
        self._leeway = leeway
        self._base = base_resolver

    def _principal_from_claims(self, claims: dict[str, Any]) -> Principal:
        sub = claims.get("sub", "unknown")
        tenant = claims.get("tenant", claims.get("hd", "default"))
        groups: list[str] = claims.get("groups", [])
        roles: list[Role] = []
        for g in groups:
            role_name = self._groups_mapping.get(g, str(g).lower())
            if role_name in BUILTIN_ROLES:
                roles.append(BUILTIN_ROLES[role_name])
        if not roles:
            roles = [BUILTIN_ROLES["visitor"]]  # default minimum grant
        return Principal(subject=sub, tenant=tenant, roles=roles)

    def verify_token(self, token: str, *, jwks: dict[str, Any] | None = None) -> Principal:
        """Validate a Bearer JWT (using injected or provided JWKS) and map to a Principal."""
        keys = jwks if jwks is not None else self._jwks
        if keys is None:
            raise OidcAuthError("no JWKS configured")
        try:
            claims = jwt.decode(
                token,
                keys,
                algorithms=["RS256", "ES256"],
                audience=self._audience,
                options={"leeway": self._leeway},
            )
        except ExpiredSignatureError as exc:
            raise OidcAuthError("token expired") from exc
        except JWTError as exc:
            raise OidcAuthError(f"invalid token: {exc}") from exc
        return self._principal_from_claims(claims)

    def resolve_api_key(self, api_key: str | None) -> Principal:
        """Delegate to the base API-key resolver (service-account path)."""
        if self._base is not None:
            return self._base.resolve(api_key)
        return ANONYMOUS
