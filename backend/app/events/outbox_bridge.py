"""Bridge: domain events -> transactional outbox -> webhook delivery.

This is what makes the outbox load-bearing rather than decorative. Instead of webhooks
firing inline (and being lost if delivery fails after the request commits), the bridge
subscribes to the event bus and *enqueues* each event into the outbox. A separate relay —
driven by the scheduler in production, or called explicitly — drains the outbox to the
webhook dispatcher with retries and dead-lettering.

Flow:
    agent -> EventBus.publish(event)
          -> OutboxBridge handler enqueues into Outbox (durable)
    scheduler/relay -> Outbox.relay(webhook_sink)
                    -> WebhookDispatcher delivers to subscribers (signed, retried)
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass

from app.events.bus import DomainEvent, EventBus
from app.outbox.store import Outbox, OutboxMessage
from app.webhooks.dispatcher import WebhookDispatcher


def _event_payload(event: DomainEvent) -> dict:
    """Serialise a domain event to a plain dict for durable storage."""
    if is_dataclass(event):
        return {k: v for k, v in asdict(event).items()}
    return {"name": event.name}  # pragma: no cover - all events are dataclasses


class OutboxBridge:
    """Subscribes event names to the outbox so published events are durably queued."""

    def __init__(self, bus: EventBus, outbox: Outbox, *, tenant: str = "default") -> None:
        self._bus = bus
        self._outbox = outbox
        self._tenant = tenant

    def bridge(self, *event_names: str) -> None:
        """Route the named events into the outbox when published."""
        for name in event_names:
            self._bus.subscribe(name, self._make_handler(name))

    def _make_handler(self, name: str):
        async def handler(event: DomainEvent) -> None:
            self._outbox.enqueue(name, _event_payload(event), tenant=self._tenant)

        return handler


class WebhookOutboxSink:
    """An outbox sink that delivers a message to webhook subscribers.

    Delivery failure (no successful subscriber, or an error) raises so the outbox keeps the
    message PENDING and retries it on the next relay — the whole point of the outbox.
    """

    def __init__(self, dispatcher: WebhookDispatcher) -> None:
        self._dispatcher = dispatcher

    async def __call__(self, message: OutboxMessage) -> None:
        tenant = str(message.metadata.get("tenant", "default"))
        results = await self._dispatcher.dispatch(message.topic, tenant, message.payload)
        # If there were subscribers but none accepted, treat as a failure to trigger retry.
        if results and not any(r.delivered for r in results):
            raise RuntimeError(f"no successful delivery for {message.topic}")
