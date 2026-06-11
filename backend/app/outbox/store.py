"""Transactional outbox for reliable event/webhook delivery.

Problem: publishing an event inline with a request means a delivery failure after the main
work commits is lost. The outbox decouples the two: work records a message in the outbox
(same logical transaction), and a separate relay drains pending messages to their sink with
retries and a dead-letter state. In-memory here; a real deployment persists the outbox in
the same DB as the business data so the write is atomic.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable


class MessageState(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD = "dead"


@dataclass
class OutboxMessage:
    """A message awaiting delivery."""

    id: str
    topic: str
    payload: dict
    state: MessageState = MessageState.PENDING
    attempts: int = 0
    max_attempts: int = 5
    created_at: float = 0.0
    last_error: str | None = None
    metadata: dict = field(default_factory=dict)


# A sink delivers a message; raising indicates failure.
Sink = Callable[[OutboxMessage], Awaitable[None]]


class Outbox:
    """In-memory transactional outbox with a relay."""

    def __init__(self, *, clock: Callable[[], float] = time.time) -> None:
        self._messages: dict[str, OutboxMessage] = {}
        self._clock = clock

    def enqueue(
        self, topic: str, payload: dict, *, max_attempts: int = 5, **metadata: object
    ) -> OutboxMessage:
        """Record a message for later delivery (the 'transactional' write)."""
        message = OutboxMessage(
            id=uuid.uuid4().hex[:16],
            topic=topic,
            payload=payload,
            created_at=self._clock(),
            max_attempts=max_attempts,
            metadata=dict(metadata),
        )
        self._messages[message.id] = message
        return message

    def pending(self) -> list[OutboxMessage]:
        """Messages still awaiting delivery, oldest first."""
        items = [m for m in self._messages.values() if m.state == MessageState.PENDING]
        return sorted(items, key=lambda m: m.created_at)

    async def relay(self, sink: Sink) -> dict[str, int]:
        """Attempt delivery of all pending messages; return a counts summary."""
        delivered = 0
        failed = 0
        dead = 0
        for message in self.pending():
            message.attempts += 1
            try:
                await sink(message)
                message.state = MessageState.DELIVERED
                message.last_error = None
                delivered += 1
            except Exception as exc:  # noqa: BLE001 - capture and classify
                message.last_error = str(exc)
                if message.attempts >= message.max_attempts:
                    message.state = MessageState.DEAD
                    dead += 1
                else:
                    message.state = MessageState.PENDING
                    failed += 1
        return {"delivered": delivered, "failed": failed, "dead": dead}

    def dead_letters(self) -> list[OutboxMessage]:
        """Messages that exhausted their attempts."""
        return [m for m in self._messages.values() if m.state == MessageState.DEAD]

    def get(self, message_id: str) -> OutboxMessage | None:
        return self._messages.get(message_id)

    def stats(self) -> dict[str, int]:
        """Counts by state."""
        result = {state.value: 0 for state in MessageState}
        for message in self._messages.values():
            result[message.state.value] += 1
        return result

    @property
    def size(self) -> int:
        return len(self._messages)
