"""Per-tenant usage metering and monthly quotas.

Distinct from rate limiting (which smooths bursts): metering accumulates billable usage
per tenant per period and enforces a hard monthly quota. Periods are derived from an
injected clock so tests can roll the calendar deterministically. Exceeding quota raises a
typed error the API maps to 429.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from app.errors.exceptions import RoverError


class QuotaExceededError(RoverError):
    """Raised when a tenant exceeds its quota for the current period."""

    status_code = 429
    code = "quota_exceeded"
    title = "Quota Exceeded"


def _period_key(ts: float) -> str:
    """Return a YYYY-MM period key for a timestamp (UTC)."""
    t = time.gmtime(ts)
    return f"{t.tm_year:04d}-{t.tm_mon:02d}"


@dataclass
class TenantUsage:
    """Usage counters for a tenant in a period."""

    tenant: str
    period: str
    count: int = 0
    by_action: dict[str, int] = field(default_factory=dict)


class UsageMeter:
    """Accumulates usage and enforces monthly quotas per tenant."""

    def __init__(
        self,
        *,
        default_quota: int = 100000,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.default_quota = default_quota
        self._clock = clock
        self._quotas: dict[str, int] = {}
        self._usage: dict[tuple[str, str], TenantUsage] = {}
        self._lock = threading.Lock()

    def set_quota(self, tenant: str, quota: int) -> None:
        """Override the quota for a tenant."""
        self._quotas[tenant] = quota

    def quota_for(self, tenant: str) -> int:
        return self._quotas.get(tenant, self.default_quota)

    def _bucket(self, tenant: str) -> TenantUsage:
        period = _period_key(self._clock())
        key = (tenant, period)
        usage = self._usage.get(key)
        if usage is None:
            usage = TenantUsage(tenant=tenant, period=period)
            self._usage[key] = usage
        return usage

    def record(self, tenant: str, action: str, amount: int = 1) -> TenantUsage:
        """Record usage, raising if it would exceed the tenant's quota."""
        with self._lock:
            usage = self._bucket(tenant)
            if usage.count + amount > self.quota_for(tenant):
                raise QuotaExceededError(
                    f"tenant '{tenant}' exceeded quota {self.quota_for(tenant)}"
                )
            usage.count += amount
            usage.by_action[action] = usage.by_action.get(action, 0) + amount
            return usage

    def current(self, tenant: str) -> TenantUsage:
        """Return current-period usage for a tenant (read-only snapshot)."""
        with self._lock:
            return self._bucket(tenant)

    def remaining(self, tenant: str) -> int:
        """Remaining quota for the tenant this period."""
        with self._lock:
            return max(0, self.quota_for(tenant) - self._bucket(tenant).count)
