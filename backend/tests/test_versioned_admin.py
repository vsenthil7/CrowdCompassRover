"""Tests for versioned persistence, saved searches, and the admin service."""
from __future__ import annotations

import pytest

from app.admin.service import AdminService
from app.flags.feature_flags import FeatureFlag, FeatureFlags
from app.ingestion.pipeline import FreshnessTracker, IngestionPipeline
from app.ingestion.sources import StaticFeedSource
from app.models.domain import VenueCategory
from app.persistence.memory import InMemoryEventRepository
from app.persistence.saved_search import SavedSearch, SavedSearchService
from app.persistence.versioned import ConcurrencyError, VersionedRepository
from app.resilience.cache import TTLCache


# --- versioned repo ---


async def test_versioned_create_and_get():
    repo: VersionedRepository[str, str] = VersionedRepository()
    entry = await repo.create("k", "v")
    assert entry.version == 1
    got = await repo.get("k")
    assert got.value == "v"
    assert await repo.count() == 1


async def test_versioned_create_conflict():
    repo: VersionedRepository[str, str] = VersionedRepository()
    await repo.create("k", "v")
    with pytest.raises(ConcurrencyError):
        await repo.create("k", "v2")


async def test_versioned_update_success():
    repo: VersionedRepository[str, str] = VersionedRepository()
    await repo.create("k", "v")
    updated = await repo.update("k", "v2", expected_version=1)
    assert updated.version == 2
    assert updated.value == "v2"


async def test_versioned_update_missing():
    repo: VersionedRepository[str, str] = VersionedRepository()
    with pytest.raises(ConcurrencyError):
        await repo.update("k", "v", expected_version=1)


async def test_versioned_update_version_mismatch():
    repo: VersionedRepository[str, str] = VersionedRepository()
    await repo.create("k", "v")
    with pytest.raises(ConcurrencyError):
        await repo.update("k", "v2", expected_version=99)


async def test_versioned_upsert_and_delete():
    repo: VersionedRepository[str, str] = VersionedRepository()
    e1 = await repo.upsert("k", "v")
    assert e1.version == 1
    e2 = await repo.upsert("k", "v2")
    assert e2.version == 2
    assert await repo.delete("k") is True
    assert await repo.delete("k") is False


# --- saved searches ---


async def test_saved_search_save_get_delete():
    svc = SavedSearchService(id_factory=lambda: "fixed-id", clock=lambda: 100.0)
    saved = await svc.save("owner1", "halal food", "My spots", tags=["food"])
    assert saved.id == "fixed-id"
    assert saved.created_at == 100.0
    got = await svc.get("owner1", "fixed-id")
    assert got.query == "halal food"
    assert await svc.count() == 1
    assert await svc.delete("owner1", "fixed-id") is True


async def test_saved_search_isolation_between_owners():
    svc = SavedSearchService(id_factory=lambda: "id1")
    await svc.save("owner1", "q", "l")
    # owner2 cannot see owner1's search
    assert await svc.get("owner2", "id1") is None


def test_saved_search_dataclass():
    s = SavedSearch(id="i", owner="o", query="q", label="l", created_at=1.0)
    assert s.tags == []


# --- admin ---


def _admin() -> AdminService:
    repo = InMemoryEventRepository()
    rec = {
        "name": "Test Stadium",
        "city": "NYC",
        "location": {"lat": 40.0, "lon": -74.0},
    }
    source = StaticFeedSource("feed", VenueCategory.STADIUM, [rec])
    return AdminService(
        cache=TTLCache(),
        events=repo,
        pipeline=IngestionPipeline([source]),
        freshness=FreshnessTracker(),
        flags=FeatureFlags([FeatureFlag("f", enabled=True, rollout_percent=100.0)]),
    )


async def test_admin_flush_cache():
    admin = _admin()
    await admin._cache.set("k", ["v"])
    result = await admin.flush_cache()
    assert result["flushed"] is True
    assert admin._cache.size == 0


async def test_admin_reindex():
    admin = _admin()
    result = await admin.reindex()
    assert result.indexed == 1
    assert result.healthy is True
    assert await admin._events.count() == 1


async def test_admin_status():
    admin = _admin()
    await admin.reindex()
    status = await admin.status()
    assert status["events"] == 1
    assert "cache_hit_rate" in status
    assert status["flags"] == {"f": True}
    assert status["data_stale"] is False


def test_admin_flags_snapshot():
    admin = _admin()
    assert admin.flags_snapshot() == {"f": True}
