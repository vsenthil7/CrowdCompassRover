"""Async retry with exponential backoff and jitter.

Used to wrap flaky upstream calls (Elastic MCP, Gemini). Backoff is deterministic when a
fixed ``sleep`` and ``rng`` are injected, which keeps the unit tests fast and stable.
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


@dataclass
class RetryPolicy:
    """Configuration for retrying an async operation."""

    max_attempts: int = 3
    base_delay: float = 0.1
    max_delay: float = 2.0
    multiplier: float = 2.0
    jitter: float = 0.1

    def delay_for(self, attempt: int, rand: float) -> float:
        """Compute the delay before ``attempt`` (1-indexed retries)."""
        raw = self.base_delay * (self.multiplier ** (attempt - 1))
        capped = min(raw, self.max_delay)
        return capped + rand * self.jitter


async def retry_async(
    op: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    *,
    retry_on: tuple[type[Exception], ...] = (Exception,),
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    rng: Callable[[], float] = random.random,
) -> T:
    """Invoke ``op`` with retries per ``policy``.

    Re-raises the last exception once attempts are exhausted. Exceptions not in
    ``retry_on`` propagate immediately.
    """
    last_exc: Exception | None = None
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return await op()
        except retry_on as exc:  # type: ignore[misc]
            last_exc = exc
            if attempt >= policy.max_attempts:
                break
            await sleep(policy.delay_for(attempt, rng()))
    assert last_exc is not None  # pragma: no cover - loop guarantees assignment
    raise last_exc
