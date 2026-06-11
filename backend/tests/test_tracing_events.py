"""Tests for distributed tracing and the event bus."""
from __future__ import annotations

import pytest

from app.events.bus import (
    DomainEvent,
    EventBus,
    RouteRequested,
    SearchPerformed,
    ZeroResult,
)
from app.tracing.tracer import SpanExporter, Tracer


# --- tracing ---


def test_tracer_records_span():
    tracer = Tracer()
    with tracer.start("op", foo="bar") as span:
        span.set_attribute("k", 1)
    spans = tracer.exporter.finished()
    assert len(spans) == 1
    assert spans[0].name == "op"
    assert spans[0].attributes["foo"] == "bar"
    assert spans[0].attributes["k"] == 1
    assert spans[0].status == "ok"
    assert spans[0].duration_ms >= 0


def test_tracer_nested_spans_share_trace_id():
    tracer = Tracer()
    with tracer.start("parent"):
        assert tracer.current_trace_id() is not None
        with tracer.start("child"):
            pass
    spans = {s.name: s for s in tracer.exporter.finished()}
    assert spans["parent"].trace_id == spans["child"].trace_id
    assert spans["child"].parent_id == spans["parent"].span_id
    assert spans["parent"].parent_id is None


def test_tracer_records_error_status():
    tracer = Tracer()
    with pytest.raises(ValueError):
        with tracer.start("boom"):
            raise ValueError("nope")
    span = tracer.exporter.finished()[0]
    assert span.status == "error"
    assert "nope" in str(span.attributes["error"])


def test_tracer_set_status():
    tracer = Tracer()
    with tracer.start("op") as span:
        span.set_status("degraded")
    assert tracer.exporter.finished()[0].status == "degraded"


def test_tracer_current_trace_id_none_outside_span():
    assert Tracer().current_trace_id() is None


def test_exporter_by_trace_and_clear():
    exporter = SpanExporter(maxlen=5)
    tracer = Tracer(exporter=exporter)
    with tracer.start("a"):
        pass
    tid = exporter.finished()[0].trace_id
    assert len(exporter.by_trace(tid)) == 1
    assert exporter.by_trace("missing") == []
    assert exporter.count == 1
    exporter.clear()
    assert exporter.count == 0


def test_exporter_ring_buffer_bounded():
    exporter = SpanExporter(maxlen=2)
    tracer = Tracer(exporter=exporter)
    for i in range(4):
        with tracer.start(f"op{i}"):
            pass
    assert exporter.count == 2


# --- events ---


async def test_event_bus_publish_to_subscribers():
    bus = EventBus()
    received = []

    async def handler(event: DomainEvent) -> None:
        received.append(event.name)

    bus.subscribe("search.performed", handler)
    ran = await bus.publish(SearchPerformed(query="q", language="en", result_count=3))
    assert ran == 1
    assert received == ["search.performed"]
    assert bus.published_count == 1


async def test_event_bus_no_subscribers():
    bus = EventBus()
    ran = await bus.publish(ZeroResult(query="q", language="en"))
    assert ran == 0


async def test_event_bus_isolates_handler_failure():
    bus = EventBus()
    good = []

    async def bad(_e):
        raise RuntimeError("boom")

    async def good_handler(_e):
        good.append(1)

    bus.subscribe("route.requested", bad)
    bus.subscribe("route.requested", good_handler)
    ran = await bus.publish(RouteRequested(destination="X", cheapest_mode="walk"))
    assert ran == 1  # only the good one counted
    assert good == [1]


def test_event_bus_handler_count():
    bus = EventBus()
    bus.subscribe("x", lambda e: None)  # type: ignore[arg-type,return-value]
    assert bus.handler_count("x") == 1
    assert bus.handler_count("y") == 0


def test_domain_event_default_name():
    assert DomainEvent().name == "domain.event"
