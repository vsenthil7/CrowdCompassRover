"""Role-based access control model.

Defines permissions, roles (sets of permissions), and principals (an authenticated caller
with roles and a tenant). The policy engine answers "may this principal perform this
action?" Pure data + a small evaluator, so it is trivially testable and has no framework
coupling.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Permission(str, Enum):
    """Discrete capabilities that can be granted to roles."""

    SEARCH = "search"
    CHAT = "chat"
    ROUTE = "route"
    SAVE_SEARCH = "save_search"
    VIEW_ANALYTICS = "view_analytics"
    VIEW_TRACES = "view_traces"
    ADMIN_CACHE = "admin_cache"
    ADMIN_REINDEX = "admin_reindex"
    MANAGE_WEBHOOKS = "manage_webhooks"
    EXPORT_DATA = "export_data"
    PURGE_DATA = "purge_data"


@dataclass(frozen=True)
class Role:
    """A named set of permissions."""

    name: str
    permissions: frozenset[Permission]

    def grants(self, permission: Permission) -> bool:
        return permission in self.permissions


# Built-in roles, least-privilege first.
ROLE_VISITOR = Role(
    "visitor",
    frozenset({Permission.SEARCH, Permission.CHAT, Permission.ROUTE, Permission.SAVE_SEARCH}),
)
ROLE_ANALYST = Role(
    "analyst",
    ROLE_VISITOR.permissions | {Permission.VIEW_ANALYTICS, Permission.VIEW_TRACES},
)
ROLE_ADMIN = Role(
    "admin",
    ROLE_ANALYST.permissions
    | {
        Permission.ADMIN_CACHE,
        Permission.ADMIN_REINDEX,
        Permission.MANAGE_WEBHOOKS,
        Permission.EXPORT_DATA,
        Permission.PURGE_DATA,
    },
)

BUILTIN_ROLES = {r.name: r for r in (ROLE_VISITOR, ROLE_ANALYST, ROLE_ADMIN)}


@dataclass
class Principal:
    """An authenticated caller."""

    subject: str
    tenant: str
    roles: list[Role] = field(default_factory=list)

    def permissions(self) -> set[Permission]:
        """Union of permissions across the principal's roles."""
        result: set[Permission] = set()
        for role in self.roles:
            result |= set(role.permissions)
        return result

    def role_names(self) -> list[str]:
        return [r.name for r in self.roles]


ANONYMOUS = Principal(subject="anonymous", tenant="public", roles=[])
