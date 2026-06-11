"""API-key authentication helpers.

Keys are supplied via the ``X-API-Key`` header and compared in constant time. When no keys
are configured (the default in mock/dev), authentication is disabled so local development
and the test suite need no secrets.
"""
from __future__ import annotations

import hmac


class ApiKeyAuthenticator:
    """Validates API keys against a configured allow-set."""

    def __init__(self, allowed_keys: set[str]) -> None:
        self._allowed = {k for k in allowed_keys if k}

    @property
    def enabled(self) -> bool:
        """Whether enforcement is active (any keys configured)."""
        return bool(self._allowed)

    def is_valid(self, candidate: str | None) -> bool:
        """Constant-time membership check; always valid when disabled."""
        if not self.enabled:
            return True
        if not candidate:
            return False
        return any(hmac.compare_digest(candidate, key) for key in self._allowed)


def parse_keys(raw: str) -> set[str]:
    """Parse a comma-separated key list from configuration."""
    return {k.strip() for k in raw.split(",") if k.strip()}
