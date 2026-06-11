"""Partner data connector framework — declarative specs + runtime status.

Lets external data sources (REST JSON APIs, etc.) be registered with a field map that
normalises their records into CityEvent domain objects for indexing. Pure data classes; the
fetch/normalise logic lives in the concrete connectors.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class ConnectorSpec:
    """Declarative specification for a partner data connector."""

    connector_id: str
    type: Literal["rest_json", "csv_gcs", "eventbrite"]
    base_url: str
    auth_header: str = ""  # e.g. "Bearer <token>"
    field_map: dict[str, str] = field(default_factory=dict)  # external -> CityEvent field
    tenant: str = "default"
    page_param: str = "page"
    per_page_param: str = "per_page"
    per_page: int = 100
    results_key: str = "results"


@dataclass
class ConnectorStatus:
    """Runtime status of a connector after a sync."""

    connector_id: str
    last_sync_at: datetime | None = None
    record_count: int = 0
    errors: list[str] = field(default_factory=list)
    healthy: bool = True
