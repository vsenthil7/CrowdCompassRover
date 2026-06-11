"""Normalise raw feed records into canonical :class:`CityEvent` documents.

Real feeds are messy: differing field names, missing coordinates, mixed casing. The
normaliser maps known aliases, fills defaults, computes the embedding, and rejects records
that cannot be made valid (returning them separately so the pipeline can report rejects).
"""
from __future__ import annotations

from app.core.embedding import embed
from app.ingestion.sources import FeedSource
from app.models.domain import CityEvent, GeoPoint, VenueCategory

# Aliases mapping common upstream field names to our schema.
_NAME_KEYS = ("name", "title", "label", "venue_name")
_DESC_KEYS = ("description", "desc", "summary", "details")
_CITY_KEYS = ("city", "host_city", "locality")
_LAT_KEYS = ("lat", "latitude", "y")
_LON_KEYS = ("lon", "lng", "longitude", "x")


def _first(record: dict, keys: tuple[str, ...]) -> object | None:
    for k in keys:
        if k in record and record[k] not in (None, ""):
            return record[k]
    return None


class NormalisationResult:
    """Outcome of normalising a batch: accepted events and rejected raw records."""

    def __init__(self) -> None:
        self.events: list[CityEvent] = []
        self.rejects: list[dict] = []

    @property
    def accepted(self) -> int:
        return len(self.events)

    @property
    def rejected(self) -> int:
        return len(self.rejects)


def normalise_record(record: dict, category: VenueCategory) -> CityEvent | None:
    """Map a single raw record to a CityEvent, or None if invalid."""
    name = _first(record, _NAME_KEYS)
    city = _first(record, _CITY_KEYS)
    lat = _first(record, _LAT_KEYS)
    lon = _first(record, _LON_KEYS)
    # Support a nested {"location": {"lat":..., "lon":...}} shape.
    location_obj = record.get("location")
    if (lat is None or lon is None) and isinstance(location_obj, dict):
        lat = location_obj.get("lat", lat)
        lon = location_obj.get("lon", lon)
    if name is None or city is None or lat is None or lon is None:
        return None
    try:
        location = GeoPoint(lat=float(lat), lon=float(lon))
    except (ValueError, TypeError):
        return None
    rec_id = str(record.get("id") or f"{category.value}-{str(name).lower().replace(' ', '-')}")
    description = _first(record, _DESC_KEYS) or str(name)
    event = CityEvent(
        id=rec_id,
        name=str(name),
        category=category,
        city=str(city),
        description=str(description),
        languages=list(record.get("languages", [])),
        location=location,
        open_now=bool(record.get("open_now", True)),
        tags=list(record.get("tags", [])),
        halal=bool(record.get("halal", False)),
        vegetarian=bool(record.get("vegetarian", False)),
        wheelchair_accessible=bool(record.get("wheelchair_accessible", False)),
        capacity=record.get("capacity"),
    )
    event.embedding = embed(event.text_blob())
    return event


async def normalise_source(source: FeedSource) -> NormalisationResult:
    """Fetch and normalise all records from a single source."""
    result = NormalisationResult()
    for raw in await source.fetch():
        event = normalise_record(raw, source.category)
        if event is None:
            result.rejects.append(raw)
        else:
            result.events.append(event)
    return result
