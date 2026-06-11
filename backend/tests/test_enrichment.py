"""Tests for route enrichment (mock + Google providers, models)."""
from __future__ import annotations

import httpx
import pytest

from app.enrichment.google_routes import GoogleRouteProvider
from app.enrichment.mock_routes import MockRouteProvider
from app.enrichment.routes import (
    RouteOption,
    RouteResult,
    TravelMode,
)
from app.models.domain import GeoPoint

NYC = GeoPoint(lat=40.8135, lon=-74.0745)
TS = GeoPoint(lat=40.758, lon=-73.985)


# --- models ---


def test_route_result_cheapest_fastest_empty():
    res = RouteResult(origin=NYC, destination=TS, options=[])
    assert res.cheapest is None
    assert res.fastest is None


def test_route_result_cheapest_fastest():
    opts = [
        RouteOption(mode=TravelMode.WALK, total_distance_km=5, total_duration_min=60, estimated_cost=0.0),
        RouteOption(mode=TravelMode.DRIVE, total_distance_km=6, total_duration_min=15, estimated_cost=9.0),
    ]
    res = RouteResult(origin=NYC, destination=TS, options=opts)
    assert res.cheapest.mode == TravelMode.WALK
    assert res.fastest.mode == TravelMode.DRIVE


# --- mock provider ---


async def test_mock_routes_all_modes():
    provider = MockRouteProvider()
    res = await provider.routes(NYC, TS, [TravelMode.WALK, TravelMode.TRANSIT, TravelMode.DRIVE])
    assert len(res.options) == 3
    # sorted by duration ascending
    durations = [o.total_duration_min for o in res.options]
    assert durations == sorted(durations)
    assert res.cheapest.estimated_cost == 0.0  # walking is free


async def test_mock_routes_costs_increase_with_mode():
    provider = MockRouteProvider()
    res = await provider.routes(NYC, TS, [TravelMode.WALK, TravelMode.DRIVE])
    walk = next(o for o in res.options if o.mode == TravelMode.WALK)
    drive = next(o for o in res.options if o.mode == TravelMode.DRIVE)
    assert drive.estimated_cost > walk.estimated_cost
    assert walk.legs[0].instruction.startswith("Walk")


# --- google provider ---


def _transport(handler):
    return httpx.MockTransport(handler)


async def test_google_routes_parses_response():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"routes": [{"distanceMeters": 5000, "duration": "900s"}]},
        )

    provider = GoogleRouteProvider("key", transport=_transport(handler))
    res = await provider.routes(NYC, TS, [TravelMode.DRIVE])
    assert len(res.options) == 1
    opt = res.options[0]
    assert opt.total_distance_km == 5.0
    assert opt.total_duration_min == 15.0
    assert opt.estimated_cost > 0
    await provider.aclose()


async def test_google_routes_skips_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"routes": []})

    provider = GoogleRouteProvider("key", transport=_transport(handler))
    res = await provider.routes(NYC, TS, [TravelMode.WALK])
    assert res.options == []
    await provider.aclose()


async def test_google_routes_zero_duration_default():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"routes": [{"distanceMeters": 1000}]})

    provider = GoogleRouteProvider("key", transport=_transport(handler))
    res = await provider.routes(NYC, TS, [TravelMode.WALK])
    assert res.options[0].total_duration_min == 0.0
    await provider.aclose()


async def test_google_routes_all_modes_mapped():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"routes": [{"distanceMeters": 2000, "duration": "600s"}]})

    provider = GoogleRouteProvider("key", transport=_transport(handler))
    res = await provider.routes(
        NYC, TS, [TravelMode.WALK, TravelMode.TRANSIT, TravelMode.BICYCLE, TravelMode.DRIVE]
    )
    assert len(res.options) == 4
    await provider.aclose()
