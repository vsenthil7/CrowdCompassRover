"""Secrets management abstraction with rotation awareness.

Decouples the app from where secrets live. ``EnvSecretProvider`` reads from a supplied
mapping (typically environment); a real deployment swaps in a Secret Manager / Vault
provider behind the same ``SecretProvider`` protocol with zero call-site changes. The
``RotatingSecret`` wrapper supports overlap windows where both the current and previous
value are accepted (so in-flight clients aren't broken during rotation).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Protocol, runtime_checkable

from app.errors.exceptions import RoverError


class SecretNotFoundError(RoverError):
    """Raised when a required secret is missing."""

    status_code = 500
    code = "secret_not_found"
    title = "Secret Not Found"


@runtime_checkable
class SecretProvider(Protocol):
    """Resolves named secrets."""

    def get(self, name: str) -> str | None:
        """Return a secret value or None if absent."""
        ...

    def require(self, name: str) -> str:
        """Return a secret value or raise if absent."""
        ...


class EnvSecretProvider:
    """Reads secrets from an in-memory mapping (env by default)."""

    def __init__(self, source: dict[str, str] | None = None, *, prefix: str = "") -> None:
        self._source = source or {}
        self._prefix = prefix

    def get(self, name: str) -> str | None:
        return self._source.get(f"{self._prefix}{name}")

    def require(self, name: str) -> str:
        value = self.get(name)
        if value is None:
            raise SecretNotFoundError(f"missing secret: {name}")
        return value


@dataclass
class RotatingSecret:
    """A secret with an optional previous value accepted during an overlap window."""

    current: str
    previous: str | None = None
    rotated_at: float = 0.0
    overlap_seconds: float = 3600.0
    _clock: Callable[[], float] = field(default=time.time, repr=False)

    def accepts(self, candidate: str) -> bool:
        """Whether a presented secret is currently valid."""
        if candidate == self.current:
            return True
        if self.previous is not None and candidate == self.previous:
            return self._clock() - self.rotated_at <= self.overlap_seconds
        return False

    def rotate(self, new_value: str) -> "RotatingSecret":
        """Rotate to a new value, keeping the old one for the overlap window."""
        return RotatingSecret(
            current=new_value,
            previous=self.current,
            rotated_at=self._clock(),
            overlap_seconds=self.overlap_seconds,
            _clock=self._clock,
        )
