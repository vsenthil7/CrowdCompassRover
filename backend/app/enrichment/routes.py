"""Route enrichment abstractions.

Implements the headline "cheapest / fastest route to the stadium now" capability. A
``RouteProvider`` computes routes between two points for a travel mode. The mock provider
derives deterministic estimates from haversine distance; the real provider calls the
Google Routes API. Selected by ``APP_MODE`` + credentials, like every other integration.
"""
from __future__ import annotations

from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from app.models.domain import GeoPoint


class TravelMode(str, Enum):
    """Supported travel modes."""

    WALK = "walk"
    TRANSIT = "transit"
    DRIVE = "drive"
    BICYCLE = "bicycle"


class RouteLeg(BaseModel):
    """A single step within a route."""

    mode: TravelMode
    instruction: str
    distance_km: float = Field(ge=0)
    duration_min: float = Field(ge=0)


class RouteOption(BaseModel):
    """A complete route option from origin to destination."""

    mode: TravelMode
    total_distance_km: float = Field(ge=0)
    total_duration_min: float = Field(ge=0)
    estimated_cost: float = Field(ge=0)
    currency: str = "USD"
    legs: list[RouteLeg] = Field(default_factory=list)


class RouteResult(BaseModel):
    """Ranked route options between two points."""

    origin: GeoPoint
    destination: GeoPoint
    options: list[RouteOption]

    @property
    def cheapest(self) -> RouteOption | None:
        """The lowest-cost option, if any."""
        return min(self.options, key=lambda o: o.estimated_cost, default=None)

    @property
    def fastest(self) -> RouteOption | None:
        """The shortest-duration option, if any."""
        return min(self.options, key=lambda o: o.total_duration_min, default=None)


@runtime_checkable
class RouteProvider(Protocol):
    """Computes route options between two points."""

    async def routes(
        self, origin: GeoPoint, destination: GeoPoint, modes: list[TravelMode]
    ) -> RouteResult:
        """Return ranked route options for the requested modes."""
        ...
