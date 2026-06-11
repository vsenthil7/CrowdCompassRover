"""Tests for the transactional outbox and secrets provider."""
from __future__ import annotations

import pytest

from app.outbox.store import MessageState, Outbox
from app.secrets.provider import (
    EnvSecretProvider,
    RotatingSecret,
    SecretNotFoundError,
)


# --- outbox ---


async def test_outbox_enqueue_and_relay_success():
    outbox = Outbox(clock=lambda: 1.0)
    outbox.enqueue("topic", {"k": "v"})
    assert outbox.size == 1
    assert len(outbox.pending()) == 1

    delivered = []

    async def sink(msg):
        delivered.append(msg.id)

    stats = await outbox.relay(sink)
    assert stats == {"delivered": 1, "failed": 0, "dead": 0}
    assert outbox.pending() == []
    assert outbox.stats()["delivered"] == 1


async def test_outbox_retry_then_dead():
    outbox = Outbox()
    outbox.enqueue("topic", {}, max_attempts=2)

    async def failing_sink(msg):
        raise RuntimeError("boom")

    s1 = await outbox.relay(failing_sink)
    assert s1["failed"] == 1  # first attempt, still pending
    s2 = await outbox.relay(failing_sink)
    assert s2["dead"] == 1  # exhausted attempts
    dead = outbox.dead_letters()
    assert len(dead) == 1
    assert dead[0].last_error == "boom"
    assert dead[0].state == MessageState.DEAD


async def test_outbox_recovers_after_transient_failure():
    outbox = Outbox()
    msg = outbox.enqueue("topic", {}, max_attempts=5)

    calls = {"n": 0}

    async def flaky(m):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")

    await outbox.relay(flaky)  # fails, back to pending
    assert outbox.get(msg.id).state == MessageState.PENDING
    await outbox.relay(flaky)  # succeeds
    assert outbox.get(msg.id).state == MessageState.DELIVERED


async def test_outbox_pending_order():
    clock = {"t": 0.0}
    outbox = Outbox(clock=lambda: clock["t"])
    clock["t"] = 1.0
    outbox.enqueue("a", {})
    clock["t"] = 2.0
    outbox.enqueue("b", {})
    pending = outbox.pending()
    assert [m.topic for m in pending] == ["a", "b"]


def test_outbox_stats_all_states():
    outbox = Outbox()
    stats = outbox.stats()
    assert set(stats) == {"pending", "delivered", "failed", "dead"}


# --- secrets ---


def test_env_secret_get_and_require():
    provider = EnvSecretProvider({"API_KEY": "abc"})
    assert provider.get("API_KEY") == "abc"
    assert provider.require("API_KEY") == "abc"
    assert provider.get("MISSING") is None


def test_env_secret_require_missing_raises():
    provider = EnvSecretProvider({})
    with pytest.raises(SecretNotFoundError):
        provider.require("X")


def test_env_secret_prefix():
    provider = EnvSecretProvider({"CC_TOKEN": "t"}, prefix="CC_")
    assert provider.get("TOKEN") == "t"


def test_rotating_secret_accepts_current():
    secret = RotatingSecret(current="new")
    assert secret.accepts("new") is True
    assert secret.accepts("other") is False


def test_rotating_secret_overlap_window():
    clock = {"t": 100.0}
    secret = RotatingSecret(
        current="v2", previous="v1", rotated_at=100.0, overlap_seconds=50.0,
        _clock=lambda: clock["t"],
    )
    assert secret.accepts("v1") is True  # within overlap
    clock["t"] = 200.0
    assert secret.accepts("v1") is False  # overlap expired
    assert secret.accepts("v2") is True


def test_rotating_secret_rotate():
    clock = {"t": 10.0}
    secret = RotatingSecret(current="v1", _clock=lambda: clock["t"])
    rotated = secret.rotate("v2")
    assert rotated.current == "v2"
    assert rotated.previous == "v1"
    assert rotated.accepts("v1") is True
    assert rotated.accepts("v2") is True
