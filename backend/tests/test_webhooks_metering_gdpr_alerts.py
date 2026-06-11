"""Tests for webhooks, usage metering, GDPR data rights, and alerting."""
from __future__ import annotations

import pytest

from app.audit.log import AuditLog
from app.conversation.session import SessionStore
from app.gdpr.data_rights import DataRightsService
from app.metering.usage import QuotaExceededError, UsageMeter, _period_key
from app.models.domain import QueryPlan, SearchFilters
from app.notifications.alerts import (
    Alert,
    AlertManager,
    AlertRule,
    Severity,
    log_channel,
)
from app.persistence.saved_search import SavedSearchService
from app.webhooks.dispatcher import (
    DeliveryResult,
    WebhookDispatcher,
    WebhookRegistry,
    WebhookSubscription,
    sign_payload,
)


# --- webhooks ---


def _sub(sid="s1", events=None, tenant="t", active=True):
    return WebhookSubscription(
        id=sid, tenant=tenant, url="https://hook", secret="secret123",
        events=events or {"search.performed"}, active=active,
    )


def test_registry_register_lookup_remove():
    reg = WebhookRegistry()
    reg.register(_sub())
    assert reg.count == 1
    assert len(reg.for_event("search.performed", "t")) == 1
    assert reg.for_event("other", "t") == []
    assert reg.for_event("search.performed", "other-tenant") == []
    assert reg.remove("s1") is True
    assert reg.remove("s1") is False


def test_registry_inactive_excluded():
    reg = WebhookRegistry()
    reg.register(_sub(active=False))
    assert reg.for_event("search.performed", "t") == []


def test_registry_all_with_tenant_filter():
    reg = WebhookRegistry()
    reg.register(_sub("a", tenant="t1"))
    reg.register(_sub("b", tenant="t2"))
    assert len(reg.all()) == 2
    assert len(reg.all(tenant="t1")) == 1


def test_sign_payload_stable():
    sig1 = sign_payload("secret", b"body")
    sig2 = sign_payload("secret", b"body")
    assert sig1 == sig2
    assert sign_payload("other", b"body") != sig1


async def test_dispatcher_delivers_signed():
    reg = WebhookRegistry()
    reg.register(_sub())
    captured = {}

    async def sender(url, headers, body):
        captured["url"] = url
        captured["sig"] = headers["X-CC-Signature"]
        captured["body"] = body
        return 200

    dispatcher = WebhookDispatcher(reg, sender)
    results = await dispatcher.dispatch("search.performed", "t", {"q": "halal"})
    assert results[0].delivered is True
    assert results[0].status_code == 200
    assert captured["sig"].startswith("sha256=")
    expected = "sha256=" + sign_payload("secret123", captured["body"])
    assert captured["sig"] == expected


async def test_dispatcher_non_2xx_not_delivered():
    reg = WebhookRegistry()
    reg.register(_sub())

    async def sender(url, headers, body):
        return 500

    dispatcher = WebhookDispatcher(reg, sender)
    results = await dispatcher.dispatch("search.performed", "t", {})
    assert results[0].delivered is False
    assert results[0].status_code == 500


async def test_dispatcher_records_failure():
    reg = WebhookRegistry()
    reg.register(_sub())

    async def sender(url, headers, body):
        raise RuntimeError("connection refused")

    from app.resilience.retry import RetryPolicy

    dispatcher = WebhookDispatcher(reg, sender, retry_policy=RetryPolicy(max_attempts=1, base_delay=0.0))
    results = await dispatcher.dispatch("search.performed", "t", {})
    assert results[0].delivered is False
    assert "connection refused" in results[0].error


async def test_dispatcher_no_subscribers():
    dispatcher = WebhookDispatcher(WebhookRegistry(), lambda u, h, b: None)  # type: ignore[arg-type]
    results = await dispatcher.dispatch("x", "t", {})
    assert results == []


def test_delivery_result_dataclass():
    r = DeliveryResult(subscription_id="s", delivered=True, status_code=200)
    assert r.delivered is True


# --- metering ---


def test_period_key_format():
    # 2026-06-01 12:00 UTC
    assert _period_key(1780315200.0).startswith("2026-")


def test_meter_records_and_remaining():
    meter = UsageMeter(default_quota=10)
    usage = meter.record("acme", "search")
    assert usage.count == 1
    assert usage.by_action["search"] == 1
    assert meter.remaining("acme") == 9


def test_meter_quota_override():
    meter = UsageMeter(default_quota=10)
    meter.set_quota("vip", 100)
    assert meter.quota_for("vip") == 100
    assert meter.quota_for("other") == 10


def test_meter_quota_exceeded():
    meter = UsageMeter(default_quota=2)
    meter.record("t", "search")
    meter.record("t", "search")
    with pytest.raises(QuotaExceededError) as exc:
        meter.record("t", "search")
    assert exc.value.status_code == 429


def test_meter_current_snapshot():
    meter = UsageMeter()
    meter.record("t", "chat", amount=3)
    current = meter.current("t")
    assert current.count == 3
    assert current.by_action["chat"] == 3


def test_meter_period_rollover():
    clock = {"t": 1780315200.0}  # June 2026
    meter = UsageMeter(default_quota=5, clock=lambda: clock["t"])
    meter.record("t", "search")
    assert meter.current("t").count == 1
    clock["t"] = 1783000000.0  # July 2026
    # New period resets usage.
    assert meter.current("t").count == 0


# --- gdpr ---


def _plan(q="halal"):
    return QueryPlan(
        original_query=q, detected_language="en", normalized_query=q,
        semantic_text=q, filters=SearchFilters(), top_k=5,
    )


async def test_gdpr_export_and_purge():
    sessions = SessionStore()
    saved = SavedSearchService(id_factory=lambda: "sid")
    audit = AuditLog()
    service = DataRightsService(sessions=sessions, saved_searches=saved, audit=audit)

    sessions.record("alice", "halal food", _plan())
    await saved.save("alice", "halal food", "My spots")
    audit.record("alice", "t", "search", "q", "success")

    doc = await service.export("alice")
    assert doc.subject == "alice"
    assert len(doc.sessions) == 1
    assert len(doc.saved_searches) == 1
    assert len(doc.audit_entries) == 1
    assert "subject" in doc.to_dict()

    result = await service.purge("alice")
    assert result.sessions_removed == 1
    assert result.saved_searches_removed == 1
    # After purge, export is empty.
    doc2 = await service.export("alice")
    assert doc2.sessions == []
    assert doc2.saved_searches == []


async def test_gdpr_export_empty_subject():
    service = DataRightsService(
        sessions=SessionStore(), saved_searches=SavedSearchService(), audit=AuditLog()
    )
    doc = await service.export("nobody")
    assert doc.sessions == []
    assert doc.saved_searches == []


async def test_gdpr_purge_nonexistent():
    service = DataRightsService(
        sessions=SessionStore(), saved_searches=SavedSearchService(), audit=AuditLog()
    )
    result = await service.purge("nobody")
    assert result.sessions_removed == 0
    assert result.saved_searches_removed == 0


# --- notifications ---


async def test_alert_fires_when_breached():
    manager = AlertManager()
    fired_alerts = []

    async def channel(alert: Alert):
        fired_alerts.append(alert)

    manager.add_channel(channel)
    manager.add_rule(
        AlertRule("high_zero", Severity.WARNING, lambda s: s.get("rate", 0) > 0.5, "too high")
    )
    fired = await manager.evaluate({"rate": 0.8})
    assert len(fired) == 1
    assert fired[0].severity == Severity.WARNING
    assert len(fired_alerts) == 1


async def test_alert_not_fired_when_ok():
    manager = AlertManager()
    manager.add_rule(AlertRule("r", Severity.WARNING, lambda s: s.get("x", 0) > 10, "msg"))
    fired = await manager.evaluate({"x": 1})
    assert fired == []


async def test_alert_cooldown_suppression():
    clock = {"t": 0.0}
    manager = AlertManager(cooldown=100.0, clock=lambda: clock["t"])
    manager.add_rule(AlertRule("r", Severity.CRITICAL, lambda s: True, "always"))
    first = await manager.evaluate({})
    assert len(first) == 1
    second = await manager.evaluate({})
    assert second == []  # suppressed within cooldown
    clock["t"] = 200.0
    third = await manager.evaluate({})
    assert len(third) == 1  # cooldown elapsed


async def test_alert_rule_count():
    manager = AlertManager()
    manager.add_rule(AlertRule("r", Severity.INFO, lambda s: False, "m"))
    assert manager.rule_count == 1


async def test_log_channel(caplog):
    import logging

    with caplog.at_level(logging.WARNING, logger="alerts"):
        await log_channel(Alert(rule="r", severity=Severity.CRITICAL, message="boom", ts=1.0))
        await log_channel(Alert(rule="r2", severity=Severity.WARNING, message="warn", ts=1.0))
    assert any("alert" in rec.message for rec in caplog.records)
