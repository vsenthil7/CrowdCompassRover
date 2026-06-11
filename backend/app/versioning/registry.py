"""API versioning: a registry of supported versions with deprecation metadata.

Lets the app advertise which API versions exist, which is current, and which are deprecated
(with a sunset date). The helper produces the standard advisory headers (``Deprecation`` and
``Sunset``) so clients can migrate proactively. Pure data + formatting; routing layers decide
how to mount versioned paths.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class ApiVersion:
    """A single API version."""

    name: str  # e.g. "v1"
    released: date
    deprecated: bool = False
    sunset: date | None = None


@dataclass
class VersionRegistry:
    """Registry of API versions."""

    versions: dict[str, ApiVersion] = field(default_factory=dict)
    current: str = "v1"

    def register(self, version: ApiVersion, *, make_current: bool = False) -> None:
        self.versions[version.name] = version
        if make_current:
            self.current = version.name

    def get(self, name: str) -> ApiVersion | None:
        return self.versions.get(name)

    def is_supported(self, name: str) -> bool:
        return name in self.versions

    def deprecation_headers(self, name: str) -> dict[str, str]:
        """Advisory headers for a version (empty if current and not deprecated)."""
        version = self.versions.get(name)
        if version is None or not version.deprecated:
            return {}
        headers = {"Deprecation": "true"}
        if version.sunset is not None:
            headers["Sunset"] = version.sunset.isoformat()
        return headers

    def supported_names(self) -> list[str]:
        return sorted(self.versions)


def default_registry() -> VersionRegistry:
    """Build the default registry with v1 as current."""
    registry = VersionRegistry()
    registry.register(ApiVersion(name="v1", released=date(2026, 6, 1)), make_current=True)
    return registry
