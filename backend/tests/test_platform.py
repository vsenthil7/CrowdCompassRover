"""Tests for analytics, health checks, scheduler, and config profiles."""
from __future__ import annotations

import pytest

from app.analytics.recorder import AnalyticsRecorder
from app.core.config import AppMode, Settings
from app.core.profiles import Profile, Severity, validate_settings
from app.health.checks import (
    ComponentHealth,
    HealthRegistry,
    HealthState,
)
from app.scheduling.scheduler import Scheduler


# --- analytics ---


def test_analytics_records_and_snapshots():
    clock = {"t": 100.0}
    rec = AnalyticsRecorder(clock=lambda: clock["t"])
    rec.record("Halal food", "en", 3, category="restaurant", city="New York", duration_ms=5.0)
    rec.record("estadio", "es", 0, category="stadium")
    rec.record("halal food", "en", 2)
    snap = rec.snapshot()
    assert snap.total == 3
    assert snap.zero_result == 1
    assert round(snap.zero_result_rate, 3) == round(1 / 3, 3)
    assert snap.by_language["en"] == 2
    assert snap.by_category["restaurant"] == 1
    assert ("halal food", 2) in snap.top_queries  # case-normalised


def test_analytics_empty_snapshot():
    rec = AnalyticsRecorder()
    snap = rec.snapshot()
    assert snap.total == 0
    assert snap.zero_result_rate == 0.0
    assert rec.size == 0


def test_analytics_buffer_bounded():
    rec = AnalyticsRecorder(maxlen=2)
    for i in range(5):
        rec.record(f"q{i}", "en", 1)
    assert rec.size == 2


# --- health ---


async def test_health_empty_registry_ready():
    report = await HealthRegistry().run()
    assert report.ready is True
    assert report.state == HealthState.HEALTHY


async def test_health_all_healthy():
    reg = HealthRegistry()

    async def ok():
        return ComponentHealth("dep", HealthState.HEALTHY, "fine")

    reg.register("dep", ok)
    report = await reg.run()
    assert report.ready is True
    assert report.components[0].latency_ms >= 0
    assert report.to_dict()["ready"] is True


async def test_health_degraded_still_ready():
    reg = HealthRegistry()

    async def degraded():
        return ComponentHealth("dep", HealthState.DEGRADED, "slow")

    reg.register("dep", degraded)
    report = await reg.run()
    assert report.ready is True
    assert report.state == HealthState.DEGRADED


async def test_health_unhealthy_not_ready():
    reg = HealthRegistry()

    async def bad():
        raise RuntimeError("down")

    reg.register("dep", bad)
    report = await reg.run()
    assert report.ready is False
    assert report.state == HealthState.UNHEALTHY
    assert "down" in report.components[0].detail


async def test_health_timeout():
    import asyncio

    reg = HealthRegistry(timeout=0.01)

    async def slow():
        await asyncio.sleep(1.0)
        return ComponentHealth("dep", HealthState.HEALTHY)  # pragma: no cover

    reg.register("dep", slow)
    report = await reg.run()
    assert report.ready is False
    assert report.components[0].detail == "timeout"


# --- scheduler ---


async def test_scheduler_runs_due_jobs():
    clock = {"t": 0.0}
    sched = Scheduler(clock=lambda: clock["t"])
    calls = {"n": 0}

    async def job():
        calls["n"] += 1

    sched.every("tick", 10.0, job)
    assert sched.job_count == 1
    assert await sched.run_due() == 0  # not due yet
    clock["t"] = 11.0
    assert await sched.run_due() == 1
    assert calls["n"] == 1


async def test_scheduler_isolates_job_failure():
    clock = {"t": 100.0}
    sched = Scheduler(clock=lambda: clock["t"])

    async def bad():
        raise RuntimeError("boom")

    sched.every("bad", 1.0, bad)
    clock["t"] = 102.0
    ran = await sched.run_due()
    assert ran == 1  # ran despite failing


async def test_scheduler_start_stop():
    sched = Scheduler()
    calls = {"n": 0}

    async def job():
        calls["n"] += 1

    sched.every("tick", 0.001, job)
    sched.start(poll=0.001)
    import asyncio

    await asyncio.sleep(0.02)
    await sched.stop()
    assert calls["n"] >= 1


# --- profiles ---


def test_profile_dev_mock_ok():
    result = validate_settings(Settings(app_mode=AppMode.MOCK), Profile.DEV)
    assert result.ok is True
    assert result.issues == []


def test_profile_real_without_creds_errors():
    result = validate_settings(Settings(app_mode=AppMode.REAL), Profile.DEV)
    assert result.ok is False
    fields = {i.field for i in result.errors}
    assert "elastic_mcp_url" in fields
    assert "gemini_api_key" in fields


def test_profile_prod_rejects_mock_and_no_auth():
    result = validate_settings(Settings(app_mode=AppMode.MOCK), Profile.PROD)
    assert result.ok is False
    fields = {i.field for i in result.errors}
    assert "app_mode" in fields
    assert "api_keys" in fields


def test_profile_prod_localhost_cors_warning():
    s = Settings(
        app_mode=AppMode.REAL,
        elastic_mcp_url="http://mcp",
        elastic_mcp_api_key="k",
        gemini_api_key="g",
        api_keys="secret",
        cors_origins="http://localhost:5173",
    )
    result = validate_settings(s, Profile.PROD)
    assert result.ok is True  # only a warning
    assert any(i.severity == Severity.WARNING for i in result.warnings)


def test_profile_staging_no_keys_warning():
    s = Settings(
        app_mode=AppMode.REAL,
        elastic_mcp_url="http://mcp",
        elastic_mcp_api_key="k",
        gemini_api_key="g",
    )
    result = validate_settings(s, Profile.STAGING)
    assert result.ok is True
    assert any(i.field == "api_keys" for i in result.warnings)
