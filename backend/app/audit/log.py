"""Append-only audit log for security-relevant actions.

Each entry is hash-chained to the previous one (like a mini tamper-evident ledger): the
hash of entry N includes the hash of entry N-1, so any retroactive edit breaks the chain
and is detectable via ``verify``. Entries are immutable once recorded. A real deployment
would also ship entries to durable WORM storage.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class AuditEntry:
    """A single immutable audit record."""

    seq: int
    ts: float
    actor: str
    tenant: str
    action: str
    resource: str
    outcome: str
    prev_hash: str
    entry_hash: str
    metadata: dict = field(default_factory=dict)


def _compute_hash(
    seq: int, ts: float, actor: str, tenant: str, action: str, resource: str,
    outcome: str, prev_hash: str, metadata: dict,
) -> str:
    payload = json.dumps(
        {
            "seq": seq, "ts": ts, "actor": actor, "tenant": tenant, "action": action,
            "resource": resource, "outcome": outcome, "prev": prev_hash, "meta": metadata,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


GENESIS_HASH = "0" * 64


class AuditLog:
    """Hash-chained, append-only audit log."""

    def __init__(self, *, clock: Callable[[], float] = time.time, maxlen: int = 50000) -> None:
        from collections import deque

        self._entries: "deque[AuditEntry]" = deque(maxlen=maxlen)
        self._clock = clock
        self._seq = 0
        self._last_hash = GENESIS_HASH

    def record(
        self,
        actor: str,
        tenant: str,
        action: str,
        resource: str,
        outcome: str = "success",
        **metadata: object,
    ) -> AuditEntry:
        """Append an immutable, hash-chained entry."""
        self._seq += 1
        ts = self._clock()
        meta = dict(metadata)
        entry_hash = _compute_hash(
            self._seq, ts, actor, tenant, action, resource, outcome, self._last_hash, meta
        )
        entry = AuditEntry(
            seq=self._seq,
            ts=ts,
            actor=actor,
            tenant=tenant,
            action=action,
            resource=resource,
            outcome=outcome,
            prev_hash=self._last_hash,
            entry_hash=entry_hash,
            metadata=meta,
        )
        self._entries.append(entry)
        self._last_hash = entry_hash
        return entry

    def verify(self) -> bool:
        """Verify the hash chain is intact (no tampering)."""
        prev = GENESIS_HASH
        for entry in self._entries:
            expected = _compute_hash(
                entry.seq, entry.ts, entry.actor, entry.tenant, entry.action,
                entry.resource, entry.outcome, prev, entry.metadata,
            )
            if expected != entry.entry_hash or entry.prev_hash != prev:
                return False
            prev = entry.entry_hash
        return True

    def entries(self, *, actor: str | None = None, tenant: str | None = None) -> list[AuditEntry]:
        """Return entries, optionally filtered by actor and/or tenant."""
        result = list(self._entries)
        if actor is not None:
            result = [e for e in result if e.actor == actor]
        if tenant is not None:
            result = [e for e in result if e.tenant == tenant]
        return result

    @property
    def size(self) -> int:
        return len(self._entries)
