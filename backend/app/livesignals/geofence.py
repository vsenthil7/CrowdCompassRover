"""Geofence registry and live-signal location validator.

Validates incoming live signals against registered polygons (e.g. a stadium precinct or
fan-zone boundary) so a crowd/closure report can only be attributed to a venue if the
reporter is actually inside a known zone for that tenant. Point-in-polygon uses the standard
ray-casting test; pure geometry, no external dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GeoFence:
    """A named geofenced zone defined by a polygon ring of [lon, lat] points."""

    fence_id: str
    name: str
    tenant: str
    polygon_coords: list[list[float]]  # [[lon, lat], ...]

    def contains(self, lat: float, lon: float) -> bool:
        """Point-in-polygon via ray casting. Coordinates are GeoJSON [lon, lat]."""
        coords = self.polygon_coords
        n = len(coords)
        if n < 3:
            return False  # not a polygon
        inside = False
        x, y = lon, lat
        j = n - 1
        for i in range(n):
            xi, yi = coords[i]
            xj, yj = coords[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside


class GeofenceRegistry:
    """Stores and queries geofenced zones, scoped per tenant."""

    def __init__(self) -> None:
        self._fences: dict[str, GeoFence] = {}

    def register(self, fence: GeoFence) -> None:
        self._fences[fence.fence_id] = fence

    def remove(self, fence_id: str) -> bool:
        return self._fences.pop(fence_id, None) is not None

    def for_tenant(self, tenant: str) -> list[GeoFence]:
        return [f for f in self._fences.values() if f.tenant == tenant]

    def validate_signal(self, lat: float, lon: float, tenant: str) -> tuple[bool, str | None]:
        """Return (True, fence_id) if the point lies inside any of the tenant's fences."""
        for fence in self.for_tenant(tenant):
            if fence.contains(lat, lon):
                return True, fence.fence_id
        return False, None

    def all_fences(self, tenant: str) -> list[dict]:
        return [
            {"fence_id": f.fence_id, "name": f.name, "polygon_coords": f.polygon_coords}
            for f in self.for_tenant(tenant)
        ]
