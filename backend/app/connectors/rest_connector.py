"""REST JSON connector — paginates a remote API and normalises to CityEvent."""
from __future__ import annotations

import httpx

from app.connectors.base import ConnectorSpec
from app.models.domain import CityEvent, GeoPoint, VenueCategory


def map_record(raw: dict, field_map: dict[str, str], connector_id: str) -> CityEvent | None:
    """Apply ``field_map`` to a raw record and build a CityEvent, or None if malformed."""
    mapped: dict = {}
    for ext_key, domain_key in field_map.items():
        if ext_key in raw:
            mapped[domain_key] = raw[ext_key]

    mapped.setdefault("id", str(raw.get("id", f"{connector_id}-{abs(hash(str(raw))) % 10**8}")))
    mapped.setdefault("name", raw.get("name", raw.get("title", "Unknown")))
    mapped.setdefault("city", raw.get("city", "unknown"))
    mapped.setdefault("description", raw.get("description", ""))
    mapped.setdefault("open_now", raw.get("open_now", True))
    mapped.setdefault("category", raw.get("category", "info_kiosk"))
    loc = mapped.get("location", raw.get("location", {"lat": 0.0, "lon": 0.0}))
    if isinstance(loc, dict):
        mapped["location"] = GeoPoint(lat=loc.get("lat", 0.0), lon=loc.get("lon", 0.0))

    cat_raw = mapped.get("category", "info_kiosk")
    try:
        mapped["category"] = VenueCategory(cat_raw)
    except ValueError:
        mapped["category"] = VenueCategory.INFO_KIOSK

    try:
        return CityEvent(**mapped)
    except Exception:  # noqa: BLE001 - skip records that fail validation
        return None


class RestJsonConnector:
    """Paginates a REST JSON API and normalises records to CityEvent.

    An httpx transport can be injected so pagination is testable without a network.
    """

    def __init__(self, spec: ConnectorSpec, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._spec = spec
        self._transport = transport

    async def fetch_all(self) -> tuple[list[CityEvent], list[str]]:
        """Fetch all pages; return (events, errors)."""
        events: list[CityEvent] = []
        errors: list[str] = []
        headers: dict[str, str] = {}
        if self._spec.auth_header:
            headers["Authorization"] = self._spec.auth_header

        page = 1
        async with httpx.AsyncClient(timeout=30.0, transport=self._transport) as client:
            while True:
                try:
                    resp = await client.get(
                        self._spec.base_url,
                        params={
                            self._spec.page_param: page,
                            self._spec.per_page_param: self._spec.per_page,
                        },
                        headers=headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as exc:  # noqa: BLE001 - record and stop paging
                    errors.append(f"page {page}: {exc}")
                    break

                records = data.get(self._spec.results_key, []) if isinstance(data, dict) else data
                if not records:
                    break
                for raw in records:
                    ev = map_record(raw, self._spec.field_map, self._spec.connector_id)
                    if ev is not None:
                        events.append(ev)

                if len(records) < self._spec.per_page:
                    break
                page += 1

        return events, errors
