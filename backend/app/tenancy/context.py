"""Multi-tenancy: tenant identity, context propagation, and resolution.

A ``TenantContext`` is carried through a request via a context variable so any layer can
learn the active tenant without threading it explicitly. The resolver derives the tenant
from an authenticated principal (preferred) or an explicit header, falling back to a
configurable default. Tenant ids are validated against an allow-list when one is provided,
so an unknown tenant is rejected rather than silently creating data.
"""
from __future__ import annotations

import contextvars
import re
from dataclasses import dataclass

from app.errors.exceptions import RoverError

_TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$")

_current_tenant: contextvars.ContextVar["TenantContext | None"] = contextvars.ContextVar(
    "current_tenant", default=None
)


class UnknownTenantError(RoverError):
    """Raised when a tenant id is not recognised."""

    status_code = 400
    code = "unknown_tenant"
    title = "Unknown Tenant"


class InvalidTenantError(RoverError):
    """Raised when a tenant id is malformed."""

    status_code = 400
    code = "invalid_tenant"
    title = "Invalid Tenant"


@dataclass(frozen=True)
class TenantContext:
    """The active tenant for a unit of work."""

    tenant_id: str
    display_name: str = ""

    def scoped_key(self, key: str) -> str:
        """Namespace a storage key under this tenant."""
        return f"{self.tenant_id}::{key}"


def validate_tenant_id(tenant_id: str) -> str:
    """Validate a tenant id's shape, returning it normalised (lower-case)."""
    normalised = tenant_id.strip().lower()
    if not _TENANT_RE.match(normalised):
        raise InvalidTenantError(f"invalid tenant id: {tenant_id!r}")
    return normalised


class TenantResolver:
    """Resolves and validates tenants, optionally against an allow-list."""

    def __init__(
        self, *, default: str = "default", known: set[str] | None = None
    ) -> None:
        self.default = validate_tenant_id(default)
        self._known = {validate_tenant_id(t) for t in known} if known else None

    def is_known(self, tenant_id: str) -> bool:
        if self._known is None:
            return True
        return tenant_id in self._known

    def resolve(self, *, principal_tenant: str | None, header_tenant: str | None) -> TenantContext:
        """Resolve the effective tenant: principal first, then header, then default."""
        candidate = principal_tenant or header_tenant or self.default
        tenant_id = validate_tenant_id(candidate)
        if not self.is_known(tenant_id):
            raise UnknownTenantError(f"unknown tenant: {tenant_id}")
        return TenantContext(tenant_id=tenant_id)

    def register(self, tenant_id: str) -> None:
        """Add a tenant to the allow-list (creating the list if needed)."""
        valid = validate_tenant_id(tenant_id)
        if self._known is None:
            self._known = set()
        self._known.add(valid)


def set_current_tenant(context: TenantContext):
    """Set the active tenant; returns a token for resetting."""
    return _current_tenant.set(context)


def get_current_tenant() -> TenantContext | None:
    """Return the active tenant context, if any."""
    return _current_tenant.get()


def reset_current_tenant(token) -> None:
    """Reset the active tenant using a token from :func:`set_current_tenant`."""
    _current_tenant.reset(token)
