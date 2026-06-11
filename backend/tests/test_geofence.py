"""Tests for the geofence registry and point-in-polygon validation."""
from __future__ import annotations

from app.livesignals.geofence import GeoFence, GeofenceRegistry

# A simple square fence around the origin: lon/lat in [0,4].
SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]


def _square_fence(tenant: str = "acme") -> GeoFence:
    return GeoFence(fence_id="f1", name="Square", tenant=tenant, polygon_coords=SQUARE)


def test_point_inside():
    f = _square_fence()
    assert f.contains(lat=2.0, lon=2.0) is True


def test_point_outside():
    f = _square_fence()
    assert f.contains(lat=9.0, lon=9.0) is False
    assert f.contains(lat=2.0, lon=-1.0) is False


def test_degenerate_polygon_is_never_inside():
    f = GeoFence("f", "line", "acme", [[0.0, 0.0], [1.0, 1.0]])
    assert f.contains(lat=0.5, lon=0.5) is False


def test_registry_register_and_for_tenant():
    reg = GeofenceRegistry()
    reg.register(_square_fence("acme"))
    reg.register(GeoFence("f2", "Other", "globex", SQUARE))
    assert len(reg.for_tenant("acme")) == 1
    assert len(reg.for_tenant("globex")) == 1
    assert reg.for_tenant("nobody") == []


def test_registry_remove():
    reg = GeofenceRegistry()
    reg.register(_square_fence())
    assert reg.remove("f1") is True
    assert reg.remove("f1") is False


def test_validate_signal_inside_returns_fence_id():
    reg = GeofenceRegistry()
    reg.register(_square_fence("acme"))
    ok, fence_id = reg.validate_signal(lat=2.0, lon=2.0, tenant="acme")
    assert ok is True
    assert fence_id == "f1"


def test_validate_signal_outside_rejected():
    reg = GeofenceRegistry()
    reg.register(_square_fence("acme"))
    ok, fence_id = reg.validate_signal(lat=99.0, lon=99.0, tenant="acme")
    assert ok is False
    assert fence_id is None


def test_validate_signal_wrong_tenant_rejected():
    reg = GeofenceRegistry()
    reg.register(_square_fence("acme"))
    # Point is inside acme's fence, but globex has no fences -> rejected.
    ok, _ = reg.validate_signal(lat=2.0, lon=2.0, tenant="globex")
    assert ok is False


def test_all_fences_serialisation():
    reg = GeofenceRegistry()
    reg.register(_square_fence("acme"))
    data = reg.all_fences("acme")
    assert data == [{"fence_id": "f1", "name": "Square", "polygon_coords": SQUARE}]
