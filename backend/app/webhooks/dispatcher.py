"""Webhook subscriptions and signed, retried delivery.

External subscribers register a URL + secret for a set of event names. When a matching
domain event is published, the dispatcher POSTs a signed payload (HMAC-SHA256 over the
body) with bounded retries via the resilience retry policy. Delivery uses an injected
transport so it is fully testable offline; real deployments pass an httpx transport.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from app.resilience.retry import RetryPolicy, retry_async


@dataclass
class WebhookSubscription:
    """A registered external subscriber."""

    id: str
    tenant: str
    url: str
    secret: str
    events: set[str]
    active: bool = True


def sign_payload(secret: str, body: bytes) -> str:
    """Return the hex HMAC-SHA256 signature for a body."""
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


@dataclass
class DeliveryResult:
    """Outcome of a single webhook delivery attempt set."""

    subscription_id: str
    delivered: bool
    status_code: int | None = None
    error: str | None = None


# A sender abstracts the HTTP POST: (url, headers, body) -> status code.
Sender = Callable[[str, dict[str, str], bytes], Awaitable[int]]


class WebhookRegistry:
    """Holds webhook subscriptions, indexed for event lookup."""

    def __init__(self) -> None:
        self._subs: dict[str, WebhookSubscription] = {}

    def register(self, sub: WebhookSubscription) -> None:
        self._subs[sub.id] = sub

    def remove(self, sub_id: str) -> bool:
        return self._subs.pop(sub_id, None) is not None

    def for_event(self, event_name: str, tenant: str) -> list[WebhookSubscription]:
        """Active subscriptions for an event within a tenant."""
        return [
            s
            for s in self._subs.values()
            if s.active and s.tenant == tenant and event_name in s.events
        ]

    def all(self, tenant: str | None = None) -> list[WebhookSubscription]:
        subs = list(self._subs.values())
        if tenant is not None:
            subs = [s for s in subs if s.tenant == tenant]
        return subs

    @property
    def count(self) -> int:
        return len(self._subs)


class WebhookDispatcher:
    """Delivers events to matching subscribers with signing and retries."""

    def __init__(
        self,
        registry: WebhookRegistry,
        sender: Sender,
        *,
        retry_policy: RetryPolicy | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._registry = registry
        self._sender = sender
        self._retry = retry_policy or RetryPolicy(max_attempts=3, base_delay=0.0)
        self._clock = clock

    async def dispatch(
        self, event_name: str, tenant: str, payload: dict
    ) -> list[DeliveryResult]:
        """Deliver a payload to all matching subscribers."""
        subs = self._registry.for_event(event_name, tenant)
        results: list[DeliveryResult] = []
        body = json.dumps(
            {"event": event_name, "ts": self._clock(), "data": payload},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        for sub in subs:
            signature = sign_payload(sub.secret, body)
            headers = {
                "Content-Type": "application/json",
                "X-CC-Event": event_name,
                "X-CC-Signature": f"sha256={signature}",
            }

            async def attempt(s=sub, h=headers) -> int:
                return await self._sender(s.url, h, body)

            try:
                status = await retry_async(attempt, self._retry, retry_on=(Exception,))
                results.append(
                    DeliveryResult(
                        subscription_id=sub.id,
                        delivered=200 <= status < 300,
                        status_code=status,
                    )
                )
            except Exception as exc:  # noqa: BLE001 - record failed delivery
                results.append(
                    DeliveryResult(subscription_id=sub.id, delivered=False, error=str(exc))
                )
        return results
