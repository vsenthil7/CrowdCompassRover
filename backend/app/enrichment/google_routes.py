"""Google Routes API provider (REAL mode).

Calls the Routes API ``computeRoutes`` endpoint for each requested mode and maps responses
into our domain model. Activated when a Maps API key is present. Unit-tested via a stubbed
transport so request construction and response parsing are fully covered without a key.
"""
from __future__ import annotations

import httpx

from app.enrichment.routes import RouteLeg, RouteOption, RouteResult, TravelMode
from app.models.domain import GeoPoint

_BASE = "https://routes.googleapis.com"

_MODE_TO_GOOGLE = {
    TravelMode.WALK: "WALK",
    TravelMode.TRANSIT: "TRANSIT",
    TravelMode.BICYCLE: "BICYCLE",
    TravelMode.DRIVE: "DRIVE",
}

# Rough fare model used to estimate cost from distance (Routes API omits fares for some
# modes); kept explicit and tunable.
_COST_PER_KM = {
    TravelMode.WALK: 0.0,
    TravelMode.BICYCLE: 0.0,
    TravelMode.TRANSIT: 0.18,
    TravelMode.DRIVE: 0.95,
}
_BASE_COST = {
    TravelMode.WALK: 0.0,
    TravelMode.BICYCLE: 0.0,
    TravelMode.TRANSIT: 1.50,
    TravelMode.DRIVE: 3.00,
}


class GoogleRouteProvider:
    """Route provider backed by the Google Routes API."""

    def __init__(
        self,
        api_key: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(base_url=_BASE, timeout=timeout, transport=transport)

    async def aclose(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    def _estimate_cost(self, mode: TravelMode, distance_km: float) -> float:
        return round(_BASE_COST[mode] + _COST_PER_KM[mode] * distance_km, 2)

    async def _one(
        self, origin: GeoPoint, destination: GeoPoint, mode: TravelMode
    ) -> RouteOption | None:
        body = {
            "origin": {"location": {"latLng": {"latitude": origin.lat, "longitude": origin.lon}}},
            "destination": {
                "location": {"latLng": {"latitude": destination.lat, "longitude": destination.lon}}
            },
            "travelMode": _MODE_TO_GOOGLE[mode],
        }
        resp = await self._client.post(
            "/directions/v2:computeRoutes",
            params={"key": self._api_key},
            headers={"X-Goog-FieldMask": "routes.distanceMeters,routes.duration"},
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        routes = data.get("routes", [])
        if not routes:
            return None
        route = routes[0]
        distance_km = round(route.get("distanceMeters", 0) / 1000.0, 3)
        duration_str = route.get("duration", "0s")
        duration_min = round(int(duration_str.rstrip("s") or 0) / 60.0, 1)
        return RouteOption(
            mode=mode,
            total_distance_km=distance_km,
            total_duration_min=duration_min,
            estimated_cost=self._estimate_cost(mode, distance_km),
            legs=[
                RouteLeg(
                    mode=mode,
                    instruction=f"{mode.value} to destination",
                    distance_km=distance_km,
                    duration_min=duration_min,
                )
            ],
        )

    async def routes(
        self, origin: GeoPoint, destination: GeoPoint, modes: list[TravelMode]
    ) -> RouteResult:
        """Compute a route per mode, skipping any with no result, ranked by duration."""
        options = []
        for mode in modes:
            option = await self._one(origin, destination, mode)
            if option is not None:
                options.append(option)
        options.sort(key=lambda o: o.total_duration_min)
        return RouteResult(origin=origin, destination=destination, options=options)
