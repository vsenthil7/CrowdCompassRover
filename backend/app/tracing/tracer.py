"""Lightweight distributed tracing (OpenTelemetry-style spans).

Provides nested spans with timing, attributes, and parent/child links propagated through
the async call stack via a context variable. Spans are recorded to an in-process exporter
that can be inspected (and, in production, forwarded to an OTLP collector). Kept
dependency-free so it runs everywhere the app runs, including CI.
"""
from __future__ import annotations

import contextvars
import time
import uuid
from dataclasses import dataclass, field
from types import TracebackType
from typing import Callable

_current_span: contextvars.ContextVar["Span | None"] = contextvars.ContextVar(
    "current_span", default=None
)


@dataclass
class SpanData:
    """Immutable record of a finished span."""

    trace_id: str
    span_id: str
    parent_id: str | None
    name: str
    start: float
    end: float
    attributes: dict[str, object]
    status: str

    @property
    def duration_ms(self) -> float:
        return (self.end - self.start) * 1000


class SpanExporter:
    """Collects finished spans (bounded ring buffer)."""

    def __init__(self, maxlen: int = 2000) -> None:
        from collections import deque

        self._spans: "deque[SpanData]" = deque(maxlen=maxlen)

    def export(self, span: SpanData) -> None:
        self._spans.append(span)

    def finished(self) -> list[SpanData]:
        return list(self._spans)

    def by_trace(self, trace_id: str) -> list[SpanData]:
        return [s for s in self._spans if s.trace_id == trace_id]

    def clear(self) -> None:
        self._spans.clear()

    @property
    def count(self) -> int:
        return len(self._spans)


@dataclass
class Span:
    """An active span; use as an async or sync context manager."""

    name: str
    trace_id: str
    span_id: str
    parent_id: str | None
    exporter: SpanExporter
    clock: Callable[[], float]
    attributes: dict[str, object] = field(default_factory=dict)
    status: str = "ok"
    _start: float = 0.0
    _token: object = None

    def set_attribute(self, key: str, value: object) -> "Span":
        """Attach an attribute to the span."""
        self.attributes[key] = value
        return self

    def set_status(self, status: str) -> "Span":
        """Set the span status (e.g. 'error')."""
        self.status = status
        return self

    def __enter__(self) -> "Span":
        self._start = self.clock()
        self._token = _current_span.set(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if exc_type is not None:
            self.status = "error"
            self.attributes.setdefault("error", str(exc))
        end = self.clock()
        self.exporter.export(
            SpanData(
                trace_id=self.trace_id,
                span_id=self.span_id,
                parent_id=self.parent_id,
                name=self.name,
                start=self._start,
                end=end,
                attributes=dict(self.attributes),
                status=self.status,
            )
        )
        _current_span.reset(self._token)  # type: ignore[arg-type]
        return False


class Tracer:
    """Creates spans, threading trace/parent ids through the async context."""

    def __init__(
        self,
        exporter: SpanExporter | None = None,
        *,
        clock: Callable[[], float] = time.perf_counter,
        id_factory: Callable[[], str] = lambda: uuid.uuid4().hex[:16],
    ) -> None:
        self.exporter = exporter or SpanExporter()
        self._clock = clock
        self._id = id_factory

    def start(self, name: str, **attributes: object) -> Span:
        """Start a span as a child of the current span (if any)."""
        parent = _current_span.get()
        trace_id = parent.trace_id if parent else self._id()
        parent_id = parent.span_id if parent else None
        return Span(
            name=name,
            trace_id=trace_id,
            span_id=self._id(),
            parent_id=parent_id,
            exporter=self.exporter,
            clock=self._clock,
            attributes=dict(attributes),
        )

    def current_trace_id(self) -> str | None:
        """Return the active trace id, if a span is open."""
        span = _current_span.get()
        return span.trace_id if span else None
