"""Tests for logging, metrics, and request middleware."""
from __future__ import annotations

import json
import logging

import httpx
import pytest
from asgi_lifespan import LifespanManager

from app.observability.logging_config import (
    JsonFormatter,
    configure_logging,
    get_logger,
    log_event,
    request_id_var,
)
from app.observability.metrics import MetricsRegistry, get_metrics


def test_json_formatter_basic():
    fmt = JsonFormatter()
    record = logging.LogRecord("t", logging.INFO, "f", 1, "hello", None, None)
    out = json.loads(fmt.format(record))
    assert out["msg"] == "hello"
    assert out["level"] == "INFO"
    assert out["request_id"] == "-"


def test_json_formatter_with_fields_and_request_id():
    token = request_id_var.set("req-123")
    try:
        fmt = JsonFormatter()
        record = logging.LogRecord("t", logging.INFO, "f", 1, "msg", None, None)
        record.fields = {"a": 1}
        out = json.loads(fmt.format(record))
        assert out["a"] == 1
        assert out["request_id"] == "req-123"
    finally:
        request_id_var.reset(token)


def test_json_formatter_with_exception():
    fmt = JsonFormatter()
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = logging.LogRecord("t", logging.ERROR, "f", 1, "err", None, sys.exc_info())
    out = json.loads(fmt.format(record))
    assert "exc" in out


def test_configure_logging_and_log_event(capsys):
    configure_logging("DEBUG")
    logger = get_logger("test.evt")
    log_event(logger, logging.INFO, "structured", key="value")
    captured = capsys.readouterr()
    assert "structured" in captured.out
    assert "value" in captured.out


def test_metrics_counter_gauge_histogram_render():
    reg = MetricsRegistry()
    reg.inc("reqs", method="GET")
    reg.inc("reqs", method="GET")
    reg.set_gauge("temp", 42.0, zone="a")
    reg.observe("latency", 0.03, path="/x")
    reg.observe("latency", 3.0, path="/x")
    text = reg.render()
    assert "reqs{method=\"GET\"} 2" in text
    assert "temp{zone=\"a\"} 42.0" in text
    assert "latency_bucket" in text
    assert "latency_count" in text
    assert "latency_sum" in text


def test_metrics_time_contextmanager():
    reg = MetricsRegistry()
    with reg.time("block_seconds", op="x"):
        pass
    text = reg.render()
    assert "block_seconds_count" in text


def test_metrics_render_no_labels():
    reg = MetricsRegistry()
    reg.inc("plain")
    assert "plain 1" in reg.render()


def test_metrics_histogram_overflow_bucket():
    # A value above the largest bucket lands in the +Inf overflow bucket (line 65).
    reg = MetricsRegistry()
    reg.observe("big_latency", 99.0, path="/slow")
    text = reg.render()
    assert "big_latency_count" in text
    assert 'le="+Inf"' in text


def test_get_metrics_singleton():
    assert get_metrics() is get_metrics()


# --- middleware via a tiny app ---


@pytest.fixture
async def app_client():
    from app.api import deps
    from app.main import create_app

    deps._components = None
    app = create_app()
    async with LifespanManager(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    deps._components = None


async def test_request_id_header_roundtrip(app_client):
    r = await app_client.get("/api/health")
    assert "x-request-id" in r.headers


async def test_request_id_honoured_from_inbound(app_client):
    r = await app_client.get("/api/health", headers={"X-Request-ID": "abc123"})
    assert r.headers["x-request-id"] == "abc123"


async def test_metrics_endpoint(app_client):
    await app_client.get("/api/health")
    r = await app_client.get("/api/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text
