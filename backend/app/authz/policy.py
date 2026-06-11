"""Authorization policy engine and principal resolution.

The engine evaluates whether a principal holds a permission and raises a typed error
otherwise. The resolver maps an API key to a principal (subject, tenant, roles) using a
configurable key directory; unknown keys resolve to the anonymous principal so public
endpoints still work.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.authz.rbac import ANONYMOUS, BUILTIN_ROLES, Permission, Principal, Role
from app.errors.exceptions import RoverError


class AuthorizationError(RoverError):
    """Raised when a principal lacks a required permission."""

    status_code = 403
    code = "forbidden"
    title = "Forbidden"


@dataclass
class KeyBinding:
    """Maps an API key to identity + roles + tenant."""

    api_key: str
    subject: str
    tenant: str
    role_names: list[str]


class PrincipalResolver:
    """Resolves API keys to principals."""

    def __init__(self, bindings: list[KeyBinding] | None = None) -> None:
        self._by_key: dict[str, KeyBinding] = {b.api_key: b for b in (bindings or [])}

    def register(self, binding: KeyBinding) -> None:
        self._by_key[binding.api_key] = binding

    def resolve(self, api_key: str | None) -> Principal:
        """Return the principal for an API key, or anonymous."""
        if not api_key:
            return ANONYMOUS
        binding = self._by_key.get(api_key)
        if binding is None:
            return ANONYMOUS
        roles: list[Role] = [
            BUILTIN_ROLES[name] for name in binding.role_names if name in BUILTIN_ROLES
        ]
        return Principal(subject=binding.subject, tenant=binding.tenant, roles=roles)


class PolicyEngine:
    """Evaluates permission checks for principals."""

    def allows(self, principal: Principal, permission: Permission) -> bool:
        """Whether the principal holds the permission."""
        return permission in principal.permissions()

    def require(self, principal: Principal, permission: Permission) -> None:
        """Raise :class:`AuthorizationError` if the principal lacks the permission."""
        if not self.allows(principal, permission):
            raise AuthorizationError(
                f"{principal.subject} lacks permission '{permission.value}'"
            )
