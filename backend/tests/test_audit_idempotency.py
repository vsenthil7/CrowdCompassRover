"""Tests for the hash-chained audit log and the idempotency store."""
from __future__ import annotations

from app.audit.log import GENESIS_HASH, AuditLog
from app.idempotency.store import IdempotencyStore, KeyState


# --- audit log ---


def test_audit_records_and_chains():
    clock = {"t": 100.0}
    log = AuditLog(clock=lambda: clock["t"])
    e1 = log.record("alice", "acme", "search", "q1", "success")
    assert e1.seq == 1
    assert e1.prev_hash == GENESIS_HASH
    clock["t"] = 101.0
    e2 = log.record("alice", "acme", "search", "q2", "success")
    assert e2.seq == 2
    assert e2.prev_hash == e1.entry_hash
    assert log.size == 2


def test_audit_verify_intact():
    log = AuditLog()
    for i in range(5):
        log.record("u", "t", "action", f"r{i}")
    assert log.verify() is True


def test_audit_verify_detects_tampering():
    log = AuditLog()
    log.record("u", "t", "a", "r1")
    log.record("u", "t", "a", "r2")
    # Tamper with an entry's stored action via the internal deque.
    tampered = log._entries[0]
    object.__setattr__(tampered, "action", "MUTATED")
    assert log.verify() is False


def test_audit_filtering():
    log = AuditLog()
    log.record("alice", "t1", "a", "r")
    log.record("bob", "t2", "a", "r")
    assert len(log.entries(actor="alice")) == 1
    assert len(log.entries(tenant="t2")) == 1
    assert len(log.entries()) == 2


def test_audit_metadata_in_hash():
    log = AuditLog()
    e = log.record("u", "t", "a", "r", "success", ip="1.2.3.4")
    assert e.metadata["ip"] == "1.2.3.4"
    assert log.verify() is True


def test_audit_bounded():
    log = AuditLog(maxlen=2)
    for i in range(4):
        log.record("u", "t", "a", f"r{i}")
    assert log.size == 2


# --- idempotency ---


async def test_idempotency_new_then_completed():
    store = IdempotencyStore()
    state, cached = await store.begin("key1")
    assert state == KeyState.NEW
    assert cached is None
    await store.complete("key1", {"result": 42})
    state2, cached2 = await store.begin("key1")
    assert state2 == KeyState.COMPLETED
    assert cached2 == {"result": 42}


async def test_idempotency_in_flight():
    store = IdempotencyStore()
    await store.begin("key1")  # marks in-flight
    state, _ = await store.begin("key1")
    assert state == KeyState.IN_FLIGHT


async def test_idempotency_release():
    store = IdempotencyStore()
    await store.begin("key1")
    await store.release("key1")
    state, _ = await store.begin("key1")
    assert state == KeyState.NEW


async def test_idempotency_release_noop_when_completed():
    store = IdempotencyStore()
    await store.begin("key1")
    await store.complete("key1", "done")
    await store.release("key1")  # should not remove a completed record
    state, cached = await store.begin("key1")
    assert state == KeyState.COMPLETED
    assert cached == "done"


async def test_idempotency_expiry():
    clock = {"t": 0.0}
    store = IdempotencyStore(ttl=10.0, clock=lambda: clock["t"])
    await store.begin("key1")
    await store.complete("key1", "v")
    clock["t"] = 20.0
    state, cached = await store.begin("key1")
    assert state == KeyState.NEW  # expired
    assert cached is None


async def test_idempotency_size():
    store = IdempotencyStore()
    await store.begin("a")
    await store.begin("b")
    assert store.size == 2
