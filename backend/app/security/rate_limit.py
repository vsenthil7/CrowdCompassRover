"""Token-bucket rate limiting, keyed per client.

Each key (API key or client IP) gets a bucket that refills at ``rate`` tokens/second up to
``capacity``. A request consumes one token; an empty bucket is rejected. Time is injected
for deterministic tests.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class _Bucket:
    tokens: float
    last: float


class TokenBucketRateLimiter:
    """In-memory token-bucket limiter suitable for a single process / Cloud Run instance."""

    def __init__(
        self,
        *,
        rate: float = 5.0,
        capacity: float = 10.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.rate = rate
        self.capacity = capacity
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def _refill(self, bucket: _Bucket, now: float) -> None:
        elapsed = now - bucket.last
        bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self.rate)
        bucket.last = now

    def allow(self, key: str, cost: float = 1.0) -> bool:
        """Return True if the request is allowed, consuming ``cost`` tokens."""
        now = self._clock()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=self.capacity, last=now)
                self._buckets[key] = bucket
            else:
                self._refill(bucket, now)
            if bucket.tokens >= cost:
                bucket.tokens -= cost
                return True
            return False

    def remaining(self, key: str) -> float:
        """Tokens currently available for a key (after refill)."""
        now = self._clock()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                return self.capacity
            self._refill(bucket, now)
            return bucket.tokens
