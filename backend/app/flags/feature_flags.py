"""Runtime feature flags with percentage rollout and targeting.

Supports boolean flags, percentage rollouts (stable per-key bucketing via hashing so the
same user consistently sees the same variant), and explicit allow/deny lists. Flags are
held in a registry that can be refreshed at runtime (e.g. from a config service) without
restarts.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class FeatureFlag:
    """A single feature flag definition."""

    key: str
    enabled: bool = False
    rollout_percent: float = 0.0  # 0..100, applied when enabled
    allow: set[str] = field(default_factory=set)
    deny: set[str] = field(default_factory=set)

    def evaluate(self, subject: str | None = None) -> bool:
        """Resolve the flag for an optional subject key."""
        if subject is not None and subject in self.deny:
            return False
        if subject is not None and subject in self.allow:
            return True
        if not self.enabled:
            return False
        if self.rollout_percent >= 100.0:
            return True
        if self.rollout_percent <= 0.0:
            return False
        if subject is None:
            return False
        return _bucket(self.key, subject) < self.rollout_percent


def _bucket(flag_key: str, subject: str) -> float:
    """Stable hash bucket in [0, 100) for a (flag, subject) pair."""
    digest = hashlib.sha256(f"{flag_key}:{subject}".encode()).digest()
    # Use the first 4 bytes as an integer scaled to [0, 100).
    value = int.from_bytes(digest[:4], "big")
    return (value % 10000) / 100.0


class FeatureFlags:
    """Registry of feature flags with runtime evaluation."""

    def __init__(self, flags: list[FeatureFlag] | None = None) -> None:
        self._flags: dict[str, FeatureFlag] = {}
        for flag in flags or []:
            self._flags[flag.key] = flag

    def register(self, flag: FeatureFlag) -> None:
        """Add or replace a flag."""
        self._flags[flag.key] = flag

    def is_enabled(self, key: str, subject: str | None = None) -> bool:
        """Evaluate a flag; unknown flags are disabled."""
        flag = self._flags.get(key)
        if flag is None:
            return False
        return flag.evaluate(subject)

    def all_flags(self) -> dict[str, bool]:
        """Snapshot of all flags evaluated without a subject."""
        return {k: f.evaluate(None) for k, f in self._flags.items()}

    def refresh(self, flags: list[FeatureFlag]) -> None:
        """Replace the entire flag set (runtime reload)."""
        self._flags = {f.key: f for f in flags}

    @property
    def count(self) -> int:
        return len(self._flags)
