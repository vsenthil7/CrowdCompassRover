"""In-memory connector registry — specs + last-known status."""
from __future__ import annotations

from app.connectors.base import ConnectorSpec, ConnectorStatus


class ConnectorRegistry:
    """Stores connector specs and their most recent sync status."""

    def __init__(self) -> None:
        self._specs: dict[str, ConnectorSpec] = {}
        self._status: dict[str, ConnectorStatus] = {}

    def register(self, spec: ConnectorSpec) -> None:
        self._specs[spec.connector_id] = spec
        self._status.setdefault(spec.connector_id, ConnectorStatus(spec.connector_id))

    def remove(self, connector_id: str) -> bool:
        existed = self._specs.pop(connector_id, None) is not None
        self._status.pop(connector_id, None)
        return existed

    def get(self, connector_id: str) -> ConnectorSpec | None:
        return self._specs.get(connector_id)

    def for_tenant(self, tenant: str) -> list[ConnectorSpec]:
        return [s for s in self._specs.values() if s.tenant == tenant]

    def set_status(self, status: ConnectorStatus) -> None:
        self._status[status.connector_id] = status

    def status(self, connector_id: str) -> ConnectorStatus | None:
        return self._status.get(connector_id)
