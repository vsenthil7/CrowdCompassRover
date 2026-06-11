"""Alerting: turn operational signals into notifications.

Rules evaluate a metric/health snapshot and emit alerts at a severity when breached.
Channels receive alerts (log channel built in; a real deployment adds email/Slack/PagerDuty
channels behind the same interface). De-duplication suppresses repeated firing of the same
alert within a cooldown window.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable

from app.observability.logging_config import get_logger, log_event

_logger = get_logger("alerts")


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """A fired alert."""

    rule: str
    severity: Severity
    message: str
    ts: float
    context: dict = field(default_factory=dict)


@dataclass
class AlertRule:
    """A named predicate over a snapshot that yields a message when breached."""

    name: str
    severity: Severity
    predicate: Callable[[dict], bool]
    message: str

    def evaluate(self, snapshot: dict) -> bool:
        return self.predicate(snapshot)


# A channel delivers an alert somewhere.
Channel = Callable[[Alert], Awaitable[None]]


class AlertManager:
    """Evaluates rules against snapshots and dispatches alerts to channels."""

    def __init__(
        self,
        *,
        cooldown: float = 300.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._rules: list[AlertRule] = []
        self._channels: list[Channel] = []
        self._last_fired: dict[str, float] = {}
        self.cooldown = cooldown
        self._clock = clock

    def add_rule(self, rule: AlertRule) -> None:
        self._rules.append(rule)

    def add_channel(self, channel: Channel) -> None:
        self._channels.append(channel)

    def _suppressed(self, rule_name: str) -> bool:
        last = self._last_fired.get(rule_name)
        return last is not None and (self._clock() - last) < self.cooldown

    async def evaluate(self, snapshot: dict) -> list[Alert]:
        """Evaluate all rules; dispatch and return any (non-suppressed) alerts."""
        fired: list[Alert] = []
        for rule in self._rules:
            if not rule.evaluate(snapshot):
                continue
            if self._suppressed(rule.name):
                continue
            alert = Alert(
                rule=rule.name,
                severity=rule.severity,
                message=rule.message,
                ts=self._clock(),
                context=dict(snapshot),
            )
            self._last_fired[rule.name] = self._clock()
            fired.append(alert)
            for channel in self._channels:
                await channel(alert)
        return fired

    @property
    def rule_count(self) -> int:
        return len(self._rules)


async def log_channel(alert: Alert) -> None:
    """Built-in channel that writes alerts to the structured log."""
    log_event(
        _logger,
        logging.WARNING if alert.severity != Severity.CRITICAL else logging.ERROR,
        "alert",
        rule=alert.rule,
        severity=alert.severity.value,
        message=alert.message,
    )
