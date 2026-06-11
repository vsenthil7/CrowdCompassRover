"""Deterministic mock route provider.

Derives route options from straight-line distance with per-mode speed and cost models, so
"cheapest route" works offline and in tests. The numbers are illustrative but internally
consistent (walking is slow/free, transit cheap, driving fast/costly).
"""
from __future__ import annotations

from app.core.geo import haversine_km
from app.enrichment.routes import (
    RouteLeg,
    RouteOption,
    RouteResult,
    TravelMode,
)
from app.models.domain import GeoPoint

# Per-mode model: (avg speed km/h, cost per km, fixed base cost, road-distance factor).
_MODE_MODEL: dict[TravelMode, tuple[float, float, float, float]] = {
    TravelMode.WALK: (4.8, 0.0, 0.0, 1.15),
    TravelMode.TRANSIT: (22.0, 0.18, 1.50, 1.25),
    TravelMode.BICYCLE: (15.0, 0.0, 0.0, 1.20),
    TravelMode.DRIVE: (35.0, 0.95, 3.00, 1.30),
}

_MODE_VERB = {
    TravelMode.WALK: "Walk",
    TravelMode.TRANSIT: "Take transit",
    TravelMode.BICYCLE: "Cycle",
    TravelMode.DRIVE: "Drive",
}


class MockRouteProvider:
    """Computes deterministic route estimates from geometry."""

    def _option(
        self, mode: TravelMode, straight_km: float
    ) -> RouteOption:
        speed, per_km, base, road_factor = _MODE_MODEL[mode]
        distance = round(straight_km * road_factor, 3)
        duration = round((distance / speed) * 60, 1)
        cost = round(base + per_km * distance, 2)
        leg = RouteLeg(
            mode=mode,
            instruction=f"{_MODE_VERB[mode]} to the destination",
            distance_km=distance,
            duration_min=duration,
        )
        return RouteOption(
            mode=mode,
            total_distance_km=distance,
            total_duration_min=duration,
            estimated_cost=cost,
            legs=[leg],
        )

    async def routes(
        self, origin: GeoPoint, destination: GeoPoint, modes: list[TravelMode]
    ) -> RouteResult:
        """Return one option per requested mode, ranked by duration."""
        straight = haversine_km(origin, destination)
        options = [self._option(m, straight) for m in modes]
        options.sort(key=lambda o: o.total_duration_min)
        return RouteResult(origin=origin, destination=destination, options=options)
