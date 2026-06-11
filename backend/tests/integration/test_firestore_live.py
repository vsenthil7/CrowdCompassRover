"""P4.S2 / P4.S3 — durable Firestore persistence.

Skips unless GCP_PROJECT_ID is set AND a FirestoreEventRepository implementation exists.
The durable adapter is intentionally not in the codebase yet (it cannot be coverage-tested
without GCP); this scaffold is the executable acceptance test for when it lands.
"""
from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.integration

from app.models.domain import CityEvent, GeoPoint, VenueCategory


def _load_repo_cls():
    try:
        mod = importlib.import_module("app.persistence.firestore")
    except ModuleNotFoundError:
        pytest.skip("FirestoreEventRepository not implemented yet")
    cls = getattr(mod, "FirestoreEventRepository", None)
    if cls is None:
        pytest.skip("FirestoreEventRepository not implemented yet")
    return cls


def _event(eid="itest-1") -> CityEvent:
    return CityEvent(
        id=eid, name="Integration Cafe", category=VenueCategory.RESTAURANT,
        city="Doha", description="seeded by integration test",
        location=GeoPoint(lat=25.0, lon=51.0),
    )


async def test_firestore_create_get_roundtrip(gcp_env):
    repo_cls = _load_repo_cls()
    repo = repo_cls(project_id=gcp_env["GCP_PROJECT_ID"], collection="cc-itest")
    ev = _event()
    await repo.create(ev.id, ev)
    got = await repo.get(ev.id)
    assert got is not None and got.value.name == "Integration Cafe"
    await repo.delete(ev.id)


async def test_firestore_durability_across_instances(gcp_env):
    """P4.S3: a second repo instance sees data written by the first (true durability)."""
    repo_cls = _load_repo_cls()
    pid = gcp_env["GCP_PROJECT_ID"]
    repo_a = repo_cls(project_id=pid, collection="cc-itest")
    ev = _event("itest-durable")
    await repo_a.create(ev.id, ev)
    repo_b = repo_cls(project_id=pid, collection="cc-itest")
    got = await repo_b.get(ev.id)
    assert got is not None
    await repo_b.delete(ev.id)
