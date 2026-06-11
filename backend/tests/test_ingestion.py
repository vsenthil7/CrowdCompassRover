"""Tests for ingestion sources, normalizer, and pipeline."""
from __future__ import annotations

from app.ingestion.normalizer import (
    NormalisationResult,
    normalise_record,
    normalise_source,
)
from app.ingestion.pipeline import FreshnessTracker, IngestionPipeline
from app.ingestion.sources import StaticFeedSource
from app.models.domain import VenueCategory


def _good_record():
    return {
        "id": "r1",
        "name": "Test Stadium",
        "city": "New York",
        "lat": 40.0,
        "lon": -74.0,
        "tags": ["matchday"],
        "open_now": True,
    }


async def test_static_source_fetch():
    src = StaticFeedSource("s", VenueCategory.STADIUM, [_good_record()])
    recs = await src.fetch()
    assert len(recs) == 1


def test_normalise_good_record():
    ev = normalise_record(_good_record(), VenueCategory.STADIUM)
    assert ev is not None
    assert ev.name == "Test Stadium"
    assert ev.embedding is not None


def test_normalise_with_aliases():
    rec = {"title": "Aliased", "locality": "LA", "latitude": 1.0, "longitude": 2.0}
    ev = normalise_record(rec, VenueCategory.RESTAURANT)
    assert ev is not None
    assert ev.name == "Aliased"
    assert ev.city == "LA"


def test_normalise_nested_location():
    rec = {"name": "Nested", "city": "NYC", "location": {"lat": 40.0, "lon": -74.0}}
    ev = normalise_record(rec, VenueCategory.STADIUM)
    assert ev is not None
    assert ev.location.lat == 40.0


def test_normalise_missing_required_returns_none():
    assert normalise_record({"name": "x"}, VenueCategory.STADIUM) is None


def test_normalise_bad_coordinates_returns_none():
    rec = {"name": "x", "city": "y", "lat": "notanumber", "lon": 2.0}
    assert normalise_record(rec, VenueCategory.STADIUM) is None


def test_normalise_generates_id_when_missing():
    rec = {"name": "No Id Place", "city": "NYC", "lat": 1.0, "lon": 2.0}
    ev = normalise_record(rec, VenueCategory.FAN_ZONE)
    assert ev is not None
    assert ev.id == "fan_zone-no-id-place"


async def test_normalise_source_separates_rejects():
    src = StaticFeedSource(
        "s",
        VenueCategory.STADIUM,
        [_good_record(), {"name": "incomplete"}],
    )
    result = await normalise_source(src)
    assert result.accepted == 1
    assert result.rejected == 1


def test_normalisation_result_counts():
    r = NormalisationResult()
    assert r.accepted == 0
    assert r.rejected == 0


async def test_pipeline_empty_is_healthy():
    pipeline = IngestionPipeline([])
    report = await pipeline.run()
    assert report.events == []
    assert report.healthy is True
    assert report.total_accepted == 0


async def test_pipeline_aggregates_and_dedups():
    clock = {"t": 100.0}
    rec = _good_record()
    dup = dict(rec)  # same id -> dedup
    src1 = StaticFeedSource("s1", VenueCategory.STADIUM, [rec])
    src2 = StaticFeedSource("s2", VenueCategory.STADIUM, [dup])
    pipeline = IngestionPipeline([src1, src2], clock=lambda: clock["t"])
    report = await pipeline.run()
    assert len(report.events) == 1  # deduped by id
    assert report.total_accepted == 2
    assert report.healthy is True


async def test_pipeline_isolates_source_failure():
    class _BadSource:
        name = "bad"
        category = VenueCategory.STADIUM

        async def fetch(self):
            raise RuntimeError("upstream down")

    good = StaticFeedSource(
        "good",
        VenueCategory.STADIUM,
        [_good_record(), {"name": "incomplete-no-coords"}],
    )
    pipeline = IngestionPipeline([_BadSource(), good])
    report = await pipeline.run()
    assert report.healthy is False
    assert report.total_accepted == 1
    assert report.total_rejected == 1
    statuses = {s.name: s for s in report.statuses}
    assert statuses["bad"].ok is False
    assert statuses["bad"].error is not None


def test_freshness_tracker_lifecycle():
    clock = {"t": 0.0}
    ft = FreshnessTracker(stale_after=10.0, clock=lambda: clock["t"])
    assert ft.age_seconds is None
    assert ft.is_stale is True  # never run
    ft.mark()
    clock["t"] = 5.0
    assert ft.age_seconds == 5.0
    assert ft.is_stale is False
    clock["t"] = 20.0
    assert ft.is_stale is True
