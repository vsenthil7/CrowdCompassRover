"""Tests for retry, circuit breaker, and TTL cache."""
from __future__ import annotations

import pytest

from app.resilience.cache import TTLCache
from app.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)
from app.resilience.retry import RetryPolicy, retry_async


# --- retry ---


async def test_retry_succeeds_first_try():
    calls = {"n": 0}

    async def op():
        calls["n"] += 1
        return "ok"

    out = await retry_async(op, RetryPolicy(max_attempts=3), sleep=_no_sleep, rng=lambda: 0.0)
    assert out == "ok"
    assert calls["n"] == 1


async def test_retry_eventually_succeeds():
    calls = {"n": 0}

    async def op():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("fail")
        return "ok"

    out = await retry_async(op, RetryPolicy(max_attempts=3), sleep=_no_sleep, rng=lambda: 0.5)
    assert out == "ok"
    assert calls["n"] == 3


async def test_retry_exhausts_and_raises():
    async def op():
        raise ValueError("always")

    with pytest.raises(ValueError):
        await retry_async(op, RetryPolicy(max_attempts=2), sleep=_no_sleep, rng=lambda: 0.0)


async def test_retry_does_not_retry_unlisted_exception():
    calls = {"n": 0}

    async def op():
        calls["n"] += 1
        raise KeyError("nope")

    with pytest.raises(KeyError):
        await retry_async(
            op, RetryPolicy(max_attempts=3), retry_on=(ValueError,), sleep=_no_sleep
        )
    assert calls["n"] == 1


def test_retry_policy_delay_caps():
    p = RetryPolicy(base_delay=1.0, multiplier=10.0, max_delay=5.0, jitter=0.0)
    assert p.delay_for(1, 0.0) == 1.0
    assert p.delay_for(5, 0.0) == 5.0  # capped


async def _no_sleep(_seconds: float) -> None:
    return None


# --- circuit breaker ---


async def test_breaker_opens_after_failures():
    clock = {"t": 0.0}
    cb = CircuitBreaker("x", fail_max=2, reset_timeout=10.0, clock=lambda: clock["t"])

    async def fail():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await cb.call(fail)
    with pytest.raises(ValueError):
        await cb.call(fail)
    assert cb.state == CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        await cb.call(fail)


async def test_breaker_half_open_then_close():
    clock = {"t": 0.0}
    cb = CircuitBreaker("x", fail_max=1, reset_timeout=5.0, clock=lambda: clock["t"])

    async def fail():
        raise ValueError("boom")

    async def ok():
        return "ok"

    with pytest.raises(ValueError):
        await cb.call(fail)
    assert cb.state == CircuitState.OPEN
    clock["t"] = 6.0  # past reset timeout
    assert cb.state == CircuitState.HALF_OPEN
    out = await cb.call(ok)
    assert out == "ok"
    assert cb.state == CircuitState.CLOSED


async def test_breaker_half_open_failure_reopens():
    clock = {"t": 0.0}
    cb = CircuitBreaker("x", fail_max=1, reset_timeout=5.0, clock=lambda: clock["t"])

    async def fail():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await cb.call(fail)
    clock["t"] = 6.0
    assert cb.state == CircuitState.HALF_OPEN
    with pytest.raises(ValueError):
        await cb.call(fail)
    assert cb.state == CircuitState.OPEN


# --- cache ---


async def test_cache_set_get_hit_miss():
    clock = {"t": 0.0}
    cache: TTLCache[str] = TTLCache(maxsize=2, ttl=10.0, clock=lambda: clock["t"])
    assert await cache.get("a") is None  # miss
    await cache.set("a", "1")
    assert await cache.get("a") == "1"  # hit
    assert cache.hits == 1
    assert cache.misses == 1
    assert cache.hit_rate == 0.5


async def test_cache_expiry():
    clock = {"t": 0.0}
    cache: TTLCache[str] = TTLCache(ttl=5.0, clock=lambda: clock["t"])
    await cache.set("a", "1")
    clock["t"] = 6.0
    assert await cache.get("a") is None


async def test_cache_lru_eviction():
    cache: TTLCache[str] = TTLCache(maxsize=2, ttl=100.0)
    await cache.set("a", "1")
    await cache.set("b", "2")
    await cache.get("a")  # a recently used
    await cache.set("c", "3")  # evicts b (LRU)
    assert await cache.get("b") is None
    assert await cache.get("a") == "1"
    assert await cache.get("c") == "3"


async def test_cache_get_or_set():
    cache: TTLCache[str] = TTLCache()
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        return "v"

    assert await cache.get_or_set("k", factory) == "v"
    assert await cache.get_or_set("k", factory) == "v"
    assert calls["n"] == 1


async def test_cache_clear_and_size():
    cache: TTLCache[str] = TTLCache()
    await cache.set("a", "1")
    assert cache.size == 1
    await cache.clear()
    assert cache.size == 0


async def test_cache_empty_hit_rate():
    cache: TTLCache[str] = TTLCache()
    assert cache.hit_rate == 0.0
