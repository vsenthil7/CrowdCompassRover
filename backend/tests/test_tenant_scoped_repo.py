"""Tenant key-scoping tests for InMemoryEventRepository.

Proves cross-tenant isolation is structural: data written under one tenant is invisible
to another, across get / list_all / by_city / count / delete. Fixtures seeded at
construction live under the "default" tenant.
"""
from __future__ import annotations

import pytest

from app.models.domain import CityEvent, GeoPoint, VenueCategory
from app.persistence.memory import InMemoryEventRepository
from app.tenancy.context import (
    TenantContext,
    get_current_tenant,
    reset_current_tenant,
    set_current_tenant,
)


def _event(eid: str, city: str = "Madrid") -> CityEvent:
    return CityEvent(
        id=eid,
        name=eid,
        category=list(VenueCategory)[0],
        city=city,
        description="x",
        location=GeoPoint(lat=40.4, lon=-3.7),
        open_now=True,
    )


@pytest.fixture
def repo():
    return InMemoryEventRepository()


def _use_tenant(tid: str):
    return set_current_tenant(TenantContext(tenant_id=tid))


async def test_put_get_scoped_to_tenant(repo):
    tok = _use_tenant("acme")
    try:
        await repo.put("v1", _event("v1"))
    finally:
        reset_current_tenant(tok)

    # Another tenant cannot see acme's data.
    tok = _use_tenant("globex")
    try:
        assert await repo.get("v1") is None
        assert await repo.count() == 0
        assert await repo.list_all() == []
    finally:
        reset_current_tenant(tok)

    # acme still sees it.
    tok = _use_tenant("acme")
    try:
        got = await repo.get("v1")
        assert got is not None and got.id == "v1"
        assert await repo.count() == 1
    finally:
        reset_current_tenant(tok)


async def test_list_all_and_by_city_isolated(repo):
    tok = _use_tenant("acme")
    try:
        await repo.bulk_put([_event("a1", "Madrid"), _event("a2", "Lyon")])
    finally:
        reset_current_tenant(tok)

    tok = _use_tenant("globex")
    try:
        await repo.bulk_put([_event("g1", "Madrid")])
    finally:
        reset_current_tenant(tok)

    tok = _use_tenant("acme")
    try:
        ids = {e.id for e in await repo.list_all()}
        assert ids == {"a1", "a2"}
        madrid = await repo.by_city("madrid")
        assert {e.id for e in madrid} == {"a1"}  # not g1
    finally:
        reset_current_tenant(tok)


async def test_delete_scoped(repo):
    tok = _use_tenant("acme")
    try:
        await repo.put("v1", _event("v1"))
        assert await repo.delete("v1") is True
        assert await repo.delete("v1") is False  # already gone
    finally:
        reset_current_tenant(tok)


async def test_delete_does_not_cross_tenant(repo):
    tok = _use_tenant("acme")
    try:
        await repo.put("v1", _event("v1"))
    finally:
        reset_current_tenant(tok)

    # globex cannot delete acme's key.
    tok = _use_tenant("globex")
    try:
        assert await repo.delete("v1") is False
    finally:
        reset_current_tenant(tok)

    tok = _use_tenant("acme")
    try:
        assert await repo.get("v1") is not None
    finally:
        reset_current_tenant(tok)


async def test_no_context_uses_default_tenant():
    # Fixtures seeded at construction are visible with no active context (default).
    repo = InMemoryEventRepository([_event("seed1"), _event("seed2")])
    assert get_current_tenant() is None
    assert await repo.count() == 2
    assert await repo.get("seed1") is not None
    by_city = await repo.by_city("madrid")
    assert len(by_city) == 2

    # And a tenant other than default sees none of the seed data.
    tok = _use_tenant("acme")
    try:
        assert await repo.count() == 0
    finally:
        reset_current_tenant(tok)
