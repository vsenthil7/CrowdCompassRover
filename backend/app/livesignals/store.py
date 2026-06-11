"""Live operational signals for venues: crowd level, reported wait time, and transient
closures — the fast-changing layer on top of static opening hours.

"Open" is necessary but not sufficient for a good answer to "where can I eat *now*": a venue
that is open but mobbed on a match day, or temporarily shut for an incident, should be
demoted. These signals are intentionally ephemeral — each carries an observation timestamp
and **decays** toward "unknown" as it ages, so a stale crowd report stops influencing
ranking. Pure/deterministic given an explicit ``now``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class CrowdLevel(str, Enum):
    QUIET = "quiet"
    MODERATE = "moderate"
    BUSY = "busy"
    PACKED = "packed"
    UNKNOWN = "unknown"


# Ordinal crowd weights used to compute a ranking penalty (0 = no penalty).
_CROWD_PENALTY = {
    CrowdLevel.QUIET: 0.0,
    CrowdLevel.MODERATE: 0.25,
    CrowdLevel.BUSY: 0.6,
    CrowdLevel.PACKED: 1.0,
    CrowdLevel.UNKNOWN: 0.0,
}


@dataclass(frozen=True)
class LiveSignal:
    """A point-in-time operational observation for one venue."""

    venue_id: str
    observed_at: datetime
    crowd: CrowdLevel = CrowdLevel.UNKNOWN
    wait_minutes: int | None = None
    temporarily_closed: bool = False
    note: str = ""

    def age_seconds(self, now: datetime) -> float:
        ref = self.observed_at
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        return max(0.0, (now - ref).total_seconds())


@dataclass(frozen=True)
class ResolvedSignal:
    """A signal after freshness decay has been applied at query time."""

    crowd: CrowdLevel
    wait_minutes: int | None
    temporarily_closed: bool
    freshness: float  # 1.0 = just observed, 0.0 = fully stale
    note: str = ""

    @property
    def crowd_penalty(self) -> float:
        """Ranking penalty in [0,1], scaled by freshness (stale → no penalty)."""
        return _CROWD_PENALTY[self.crowd] * self.freshness


class LiveSignalStore:
    """In-memory store of the latest live signal per venue, with freshness decay.

    A signal older than ``ttl_seconds`` is fully stale (freshness 0); between fresh and the
    TTL it decays linearly. A transient closure is only honoured while the signal is fresh
    enough to be trusted (>= ``trust_floor`` freshness), so a day-old "closed" note doesn't
    suppress a venue forever.
    """

    def __init__(self, *, ttl_seconds: float = 3600.0, trust_floor: float = 0.25) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._ttl = ttl_seconds
        self._trust_floor = trust_floor
        self._signals: dict[str, LiveSignal] = {}

    def report(self, signal: LiveSignal) -> None:
        """Record (or replace) the latest signal for a venue."""
        existing = self._signals.get(signal.venue_id)
        if existing is None or signal.observed_at >= existing.observed_at:
            self._signals[signal.venue_id] = signal

    def freshness(self, age_seconds: float) -> float:
        """Linear freshness in [0,1] from observation age."""
        if age_seconds >= self._ttl:
            return 0.0
        return 1.0 - (age_seconds / self._ttl)

    def resolve(self, venue_id: str, now: datetime) -> ResolvedSignal | None:
        """Resolve the current decayed signal for a venue, or None if unknown/fully stale."""
        sig = self._signals.get(venue_id)
        if sig is None:
            return None
        fresh = self.freshness(sig.age_seconds(now))
        if fresh <= 0.0:
            return None
        # A closure is only trusted while reasonably fresh.
        closed = sig.temporarily_closed and fresh >= self._trust_floor
        crowd = sig.crowd if fresh >= self._trust_floor else CrowdLevel.UNKNOWN
        return ResolvedSignal(
            crowd=crowd,
            wait_minutes=sig.wait_minutes,
            temporarily_closed=closed,
            freshness=round(fresh, 6),
            note=sig.note,
        )

    def count(self) -> int:
        return len(self._signals)

    def prune_stale(self, now: datetime) -> int:
        """Drop fully-stale signals; return how many were removed."""
        stale = [vid for vid, s in self._signals.items() if self.freshness(s.age_seconds(now)) <= 0.0]
        for vid in stale:
            del self._signals[vid]
        return len(stale)
