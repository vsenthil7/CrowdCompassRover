"""Tenant-scoped storage wrapper.

Makes tenancy *enforced* rather than advisory: every key is transparently namespaced by the
active tenant, and reads/lists can only ever see that tenant's data. This is the in-memory
analogue of a row-level-security predicate or a per-tenant partition key. Wrapping a single
backing store keeps the partitioning in one tested place instead of sprinkling
``f"{tenant}:{key}"`` across call sites (which is how cross-tenant leaks happen).
"""
from __future__ import annotations

import asyncio
from typing import Generic, TypeVar

from app.tenancy.context import TenantContext

T = TypeVar("T")


class TenantScopedStore(Generic[T]):
    """A key-value store that partitions all data by tenant."""

    def __init__(self) -> None:
        # Outer key = tenant id, inner = caller key. Isolation is structural.
        self._data: dict[str, dict[str, T]] = {}
        self._lock = asyncio.Lock()

    def _partition(self, tenant: TenantContext) -> dict[str, T]:
        return self._data.setdefault(tenant.tenant_id, {})

    async def put(self, tenant: TenantContext, key: str, value: T) -> None:
        async with self._lock:
            self._partition(tenant)[key] = value

    async def get(self, tenant: TenantContext, key: str) -> T | None:
        async with self._lock:
            return self._data.get(tenant.tenant_id, {}).get(key)

    async def delete(self, tenant: TenantContext, key: str) -> bool:
        async with self._lock:
            partition = self._data.get(tenant.tenant_id)
            if partition is not None and key in partition:
                del partition[key]
                return True
            return False

    async def list_keys(self, tenant: TenantContext) -> list[str]:
        async with self._lock:
            return list(self._data.get(tenant.tenant_id, {}).keys())

    async def list_values(self, tenant: TenantContext) -> list[T]:
        async with self._lock:
            return list(self._data.get(tenant.tenant_id, {}).values())

    async def count(self, tenant: TenantContext) -> int:
        async with self._lock:
            return len(self._data.get(tenant.tenant_id, {}))

    async def tenant_ids(self) -> list[str]:
        """All tenant ids with data (operational/debug use only)."""
        async with self._lock:
            return list(self._data.keys())
