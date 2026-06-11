"""In-process asynchronous event bus with typed domain events.

Decouples side effects (analytics, cache warming, webhooks) from the request path:
publishers emit domain events; subscribers handle them. Handler failures are isolated so
one bad subscriber cannot break publication. A real deployment can bridge this to Pub/Sub
or a webhook dispatcher behind the same ``publish`` call.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from app.observability.logging_config import get_logger, log_event

_logger = get_logger("events")


@dataclass
class DomainEvent:
    """Base domain event."""

    name: str = "domain.event"


@dataclass
class SearchPerformed(DomainEvent):
    """Emitted after a search completes."""

    query: str = ""
    language: str = ""
    result_count: int = 0
    name: str = "search.performed"


@dataclass
class RouteRequested(DomainEvent):
    """Emitted after a route is computed."""

    destination: str = ""
    cheapest_mode: str | None = None
    name: str = "route.requested"


@dataclass
class ZeroResult(DomainEvent):
    """Emitted when a query returns no results (a content-gap signal)."""

    query: str = ""
    language: str = ""
    name: str = "search.zero_result"


Handler = Callable[[DomainEvent], Awaitable[None]]


@dataclass
class _Subscription:
    event_name: str
    handler: Handler


class EventBus:
    """Async pub/sub bus keyed by event name."""

    def __init__(self) -> None:
        self._subs: dict[str, list[Handler]] = {}
        self.published_count = 0

    def subscribe(self, event_name: str, handler: Handler) -> None:
        """Register a handler for an event name."""
        self._subs.setdefault(event_name, []).append(handler)

    async def publish(self, event: DomainEvent) -> int:
        """Publish an event to all subscribers; return how many handlers ran."""
        self.published_count += 1
        handlers = self._subs.get(event.name, [])
        ran = 0
        for handler in handlers:
            try:
                await handler(event)
                ran += 1
            except Exception as exc:  # noqa: BLE001 - isolate handler failures
                log_event(
                    _logger,
                    logging.ERROR,
                    "handler_failed",
                    event=event.name,
                    error=str(exc),
                )
        return ran

    def handler_count(self, event_name: str) -> int:
        """Number of handlers registered for an event name."""
        return len(self._subs.get(event_name, []))
