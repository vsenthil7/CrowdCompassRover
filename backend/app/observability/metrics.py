"""In-process metrics registry with a Prometheus text exposition format.

Deliberately dependency-free: counters, gauges, and histograms with fixed buckets, plus a
render function compatible with the Prometheus text format so the `/metrics` endpoint can
be scraped directly. Thread-safety is provided by a lock since uvicorn workers may share
the registry within a process.
"""
from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

_DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


def _label_key(labels: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(labels.items()))


@dataclass
class _Counter:
    name: str
    help: str
    values: dict[tuple, float] = field(default_factory=dict)

    def inc(self, amount: float, labels: dict[str, str]) -> None:
        key = _label_key(labels)
        self.values[key] = self.values.get(key, 0.0) + amount


@dataclass
class _Gauge:
    name: str
    help: str
    values: dict[tuple, float] = field(default_factory=dict)

    def set(self, value: float, labels: dict[str, str]) -> None:
        self.values[_label_key(labels)] = value


@dataclass
class _Histogram:
    name: str
    help: str
    buckets: tuple[float, ...] = _DEFAULT_BUCKETS
    counts: dict[tuple, list[int]] = field(default_factory=dict)
    sums: dict[tuple, float] = field(default_factory=dict)
    totals: dict[tuple, int] = field(default_factory=dict)

    def observe(self, value: float, labels: dict[str, str]) -> None:
        key = _label_key(labels)
        if key not in self.counts:
            self.counts[key] = [0] * (len(self.buckets) + 1)
            self.sums[key] = 0.0
            self.totals[key] = 0
        placed = False
        for i, edge in enumerate(self.buckets):
            if value <= edge:
                self.counts[key][i] += 1
                placed = True
                break
        if not placed:
            self.counts[key][-1] += 1
        self.sums[key] += value
        self.totals[key] += 1


class MetricsRegistry:
    """Holds all metric families and renders them."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, _Counter] = {}
        self._gauges: dict[str, _Gauge] = {}
        self._histograms: dict[str, _Histogram] = {}

    def counter(self, name: str, help: str = "") -> _Counter:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = _Counter(name, help)
            return self._counters[name]

    def gauge(self, name: str, help: str = "") -> _Gauge:
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = _Gauge(name, help)
            return self._gauges[name]

    def histogram(self, name: str, help: str = "") -> _Histogram:
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = _Histogram(name, help)
            return self._histograms[name]

    def inc(self, name: str, amount: float = 1.0, **labels: str) -> None:
        self.counter(name).inc(amount, labels)

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        self.gauge(name).set(value, labels)

    def observe(self, name: str, value: float, **labels: str) -> None:
        self.histogram(name).observe(value, labels)

    @contextmanager
    def time(self, name: str, **labels: str):
        """Context manager timing a block and observing it into a histogram."""
        start = time.perf_counter()
        try:
            yield
        finally:
            self.observe(name, time.perf_counter() - start, **labels)

    def render(self) -> str:
        """Render all metrics in Prometheus text exposition format."""
        lines: list[str] = []
        with self._lock:
            for c in self._counters.values():
                lines.append(f"# HELP {c.name} {c.help}")
                lines.append(f"# TYPE {c.name} counter")
                for key, val in c.values.items():
                    lines.append(f"{c.name}{_fmt_labels(key)} {val}")
            for g in self._gauges.values():
                lines.append(f"# HELP {g.name} {g.help}")
                lines.append(f"# TYPE {g.name} gauge")
                for key, val in g.values.items():
                    lines.append(f"{g.name}{_fmt_labels(key)} {val}")
            for h in self._histograms.values():
                lines.append(f"# HELP {h.name} {h.help}")
                lines.append(f"# TYPE {h.name} histogram")
                for key, counts in h.counts.items():
                    cumulative = 0
                    for i, edge in enumerate(h.buckets):
                        cumulative += counts[i]
                        labels = dict(key) | {"le": str(edge)}
                        lines.append(
                            f"{h.name}_bucket{_fmt_labels(_label_key(labels))} {cumulative}"
                        )
                    cumulative += counts[-1]
                    inf_labels = dict(key) | {"le": "+Inf"}
                    lines.append(
                        f"{h.name}_bucket{_fmt_labels(_label_key(inf_labels))} {cumulative}"
                    )
                    lines.append(f"{h.name}_sum{_fmt_labels(key)} {h.sums[key]}")
                    lines.append(f"{h.name}_count{_fmt_labels(key)} {h.totals[key]}")
        return "\n".join(lines) + "\n"


def _fmt_labels(key: tuple) -> str:
    if not key:
        return ""
    inner = ",".join(f'{k}="{v}"' for k, v in key)
    return "{" + inner + "}"


_registry = MetricsRegistry()


def get_metrics() -> MetricsRegistry:
    """Return the process-wide metrics registry."""
    return _registry
