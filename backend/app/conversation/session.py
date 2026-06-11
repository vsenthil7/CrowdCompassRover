"""Conversation session memory for multi-turn context.

Holds a bounded history of turns per session so the agent can resolve follow-ups like
"what about open ones?" or "and near the stadium?" by carrying forward the previous plan's
filters. Sessions expire after inactivity. Storage is pluggable; the default is in-memory.
"""
from __future__ import annotations

import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from typing import Callable, Deque

from app.models.domain import QueryPlan


@dataclass
class Turn:
    """A single user turn and the plan it produced."""

    query: str
    plan: QueryPlan
    ts: float


@dataclass
class Session:
    """A conversation session with bounded turn history."""

    session_id: str
    created_at: float
    last_active: float
    turns: Deque[Turn] = field(default_factory=lambda: deque(maxlen=20))

    def add(self, turn: Turn) -> None:
        self.turns.append(turn)
        self.last_active = turn.ts

    @property
    def last_plan(self) -> QueryPlan | None:
        return self.turns[-1].plan if self.turns else None


class SessionStore:
    """Bounded, expiring in-memory session store (LRU by capacity)."""

    def __init__(
        self,
        *,
        maxsize: int = 1000,
        ttl: float = 1800.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.maxsize = maxsize
        self.ttl = ttl
        self._clock = clock
        self._sessions: "OrderedDict[str, Session]" = OrderedDict()

    def _expired(self, session: Session) -> bool:
        return self._clock() - session.last_active > self.ttl

    def get(self, session_id: str) -> Session | None:
        """Return a live session or None."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if self._expired(session):
            del self._sessions[session_id]
            return None
        self._sessions.move_to_end(session_id)
        return session

    def get_or_create(self, session_id: str) -> Session:
        """Return the existing live session or create a new one."""
        existing = self.get(session_id)
        if existing is not None:
            return existing
        now = self._clock()
        session = Session(session_id=session_id, created_at=now, last_active=now)
        self._sessions[session_id] = session
        self._sessions.move_to_end(session_id)
        while len(self._sessions) > self.maxsize:
            self._sessions.popitem(last=False)
        return session

    def record(self, session_id: str, query: str, plan: QueryPlan) -> Session:
        """Append a turn to a session and return it."""
        session = self.get_or_create(session_id)
        session.add(Turn(query=query, plan=plan, ts=self._clock()))
        return session

    @property
    def active_count(self) -> int:
        """Number of (not-yet-evicted) sessions."""
        return len(self._sessions)

    def drop(self, session_id: str) -> bool:
        """Remove a session entirely (used for data purge); returns whether it existed."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
