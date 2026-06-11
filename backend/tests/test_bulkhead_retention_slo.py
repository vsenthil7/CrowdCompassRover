"""Tests for the concurrency bulkhead, retention sweeper, and SLO tracker."""
from __future__ import annotations

import asyncio

import pytest

from app.concurrency.bulkhead import Bulkhead, BulkheadFullError
from app.retention.sweeper import RetentionPolicy, RetentionSweeper
from app.slo.tracker import SloReport, SloTracker


# --- bulkhead ---


async def test_bulkhead_runs_within_limit():
    bh = Bulkhead("t", max_concurrent=2)

    async def work():
        return "ok"

    assert await bh.run(work) == "ok"
    assert bh.stats().active == 0


def test_bulkhead_invalid_config():
    with pytest.raises(ValueError):
        Bulkhead("t", max_concurrent=0)


async def test_bulkhead_limits_concurrency():
    bh = Bulkhead("t", max_concurrent=2)
    started = []
    release = asyncio.Event()

    async def work(i):
        started.append(i)
        await release.wait()
        return i

    tasks = [asyncio.create_task(bh.run(lambda i=i: work(i))) for i in range(3)]
    await asyncio.sleep(0.01)
    # Only 2 should have started given max_concurrent=2.
    assert len(started) == 2
    assert bh.stats().active == 2
    release.set()
    await asyncio.gather(*tasks)
    assert bh.stats().active == 0


async def test_bulkhead_rejects_when_full():
    bh = Bulkhead("t", max_concurrent=1, max_queue=0)
    release = asyncio.Event()

    async def blocker():
        await release.wait()

    task = asyncio.create_task(bh.run(blocker))
    await asyncio.sleep(0.01)

    async def extra():
        return 1

    with pytest.raises(BulkheadFullError) as exc:
        await bh.run(extra)
    assert exc.value.status_code == 503
    assert bh.stats().rejected == 1
    release.set()
    await task


async def test_bulkhead_propagates_exception_and_resets():
    bh = Bulkhead("t", max_concurrent=1)

    async def boom():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        await bh.run(boom)
    assert bh.stats().active == 0
    assert bh.stats().queued == 0


async def test_bulkhead_queue_cleanup_on_cancel():
    # A task cancelled while waiting in the queue must decrement the queued counter.
    bh = Bulkhead("t", max_concurrent=1, max_queue=10)
    release = asyncio.Event()

    async def blocker():
        await release.wait()

    holder = asyncio.create_task(bh.run(blocker))
    await asyncio.sleep(0.01)
    assert bh.stats().active == 1

    async def waiter():
        return await bh.run(lambda: asyncio.sleep(0))

    queued_task = asyncio.create_task(waiter())
    await asyncio.sleep(0.01)
    assert bh.stats().queued == 1
    queued_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await queued_task
    assert bh.stats().queued == 0
    release.set()
    await holder


# --- retention ---


class _FakeSource:
    def __init__(self, timestamps):
        self._ts = list(timestamps)

    def prune_before(self, cutoff):
        before = len(self._ts)
        self._ts = [t for t in self._ts if t >= cutoff]
        return before - len(self._ts)


async def test_retention_sweeps_old():
    clock = {"t": 1000.0}
    sweeper = RetentionSweeper(clock=lambda: clock["t"])
    source = _FakeSource([100.0, 500.0, 990.0])
    sweeper.register(RetentionPolicy("analytics", max_age_seconds=200.0), source)
    results = sweeper.sweep()
    # cutoff = 1000 - 200 = 800; only 990 survives -> 2 removed.
    assert results[0].name == "analytics"
    assert results[0].removed == 2


def test_retention_policy_count():
    sweeper = RetentionSweeper()
    sweeper.register(RetentionPolicy("a", 10), _FakeSource([]))
    sweeper.register(RetentionPolicy("b", 20), _FakeSource([]))
    assert sweeper.policy_count == 2


def test_retention_real_sources():
    from app.analytics.recorder import AnalyticsRecorder
    from app.audit.log import AuditLog

    clock = {"t": 1000.0}
    analytics = AnalyticsRecorder(clock=lambda: clock["t"])
    audit = AuditLog(clock=lambda: clock["t"])
    clock["t"] = 100.0
    analytics.record("old", "en", 1)
    audit.record("u", "t", "old", "r")
    clock["t"] = 1000.0
    analytics.record("new", "en", 1)
    audit.record("u", "t", "new", "r")

    sweeper = RetentionSweeper(clock=lambda: clock["t"])
    sweeper.register(RetentionPolicy("analytics", 200.0), analytics)
    sweeper.register(RetentionPolicy("audit", 200.0), audit)
    results = {r.name: r.removed for r in sweeper.sweep()}
    assert results["analytics"] == 1
    assert results["audit"] == 1
    # Audit chain still verifies after pruning the old prefix.
    assert audit.verify() is True


# --- slo ---


def test_slo_perfect():
    tracker = SloTracker()
    tracker.set_target("search", 0.99)
    for _ in range(100):
        tracker.record("search", True)
    report = tracker.report("search")
    assert report.success_ratio == 1.0
    assert report.meeting_slo is True
    assert report.budget_remaining == 1.0


def test_slo_breached():
    tracker = SloTracker()
    tracker.set_target("search", 0.9)
    for _ in range(80):
        tracker.record("search", True)
    for _ in range(20):
        tracker.record("search", False)
    report = tracker.report("search")
    assert report.success_ratio == 0.8
    assert report.meeting_slo is False
    # error budget = 0.1; failure ratio 0.2 -> consumed 2x -> remaining 0.
    assert report.budget_remaining == 0.0


def test_slo_partial_budget():
    tracker = SloTracker()
    tracker.set_target("chat", 0.9)
    for _ in range(95):
        tracker.record("chat", True)
    for _ in range(5):
        tracker.record("chat", False)
    report = tracker.report("chat")
    # failure ratio 0.05, budget 0.1 -> consumed 0.5 -> remaining 0.5
    assert report.budget_remaining == pytest.approx(0.5)
    assert report.meeting_slo is True


def test_slo_empty_defaults_to_perfect():
    tracker = SloTracker()
    report = tracker.report("unknown")
    assert report.success_ratio == 1.0
    assert report.total == 0
    assert report.target == 0.99


def test_slo_target_validation():
    tracker = SloTracker()
    with pytest.raises(ValueError):
        tracker.set_target("s", 0.0)
    with pytest.raises(ValueError):
        tracker.set_target("s", 1.5)


def test_slo_perfect_target_budget():
    report = SloReport(service="s", target=1.0, total=10, successes=10, failures=0)
    assert report.error_budget == 0.0
    assert report.budget_consumed == 0.0


def test_slo_perfect_target_with_failures():
    report = SloReport(service="s", target=1.0, total=10, successes=9, failures=1)
    assert report.budget_consumed == float("inf")


def test_slo_window_bounded():
    tracker = SloTracker(window=10)
    for _ in range(20):
        tracker.record("s", True)
    assert tracker.report("s").total == 10


def test_slo_services_list():
    tracker = SloTracker()
    tracker.set_target("a", 0.9)
    tracker.record("b", True)
    assert tracker.services() == ["a", "b"]
