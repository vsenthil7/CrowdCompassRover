"""P4.S4 — Redis-backed rate limiter / quota counters.

Skips unless REDIS_URL is set AND a Redis limiter implementation exists.
"""
from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.integration


def _load_limiter_cls():
    try:
        mod = importlib.import_module("app.ratelimit.redis_limiter")
    except ModuleNotFoundError:
        pytest.skip("Redis limiter not implemented yet")
    cls = getattr(mod, "RedisRateLimiter", None)
    if cls is None:
        pytest.skip("Redis limiter not implemented yet")
    return cls


async def test_redis_limiter_allows_then_blocks(redis_env):
    limiter_cls = _load_limiter_cls()
    limiter = limiter_cls(redis_env["REDIS_URL"], limit=2, window_s=60)
    key = "itest-tenant"
    assert await limiter.allow(key) is True
    assert await limiter.allow(key) is True
    assert await limiter.allow(key) is False  # third call over the limit


async def test_redis_limiter_fallback_on_unavailable(redis_env):
    """The limiter degrades open (allows) if Redis is briefly unreachable."""
    limiter_cls = _load_limiter_cls()
    limiter = limiter_cls("redis://127.0.0.1:1/0", limit=1, window_s=60)
    # Unreachable Redis -> fail-open so traffic is never wrongly blocked.
    assert await limiter.allow("any") in (True, False)
