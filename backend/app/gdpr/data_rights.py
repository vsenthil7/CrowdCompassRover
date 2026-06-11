"""GDPR / data-subject rights: export and purge.

Aggregates everything the system holds about a subject (sessions, saved searches, audit
entries) into a single export document, and purges it on request. Collaborators are passed
in via clean public APIs so this service stays decoupled and testable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.audit.log import AuditLog
from app.conversation.session import SessionStore
from app.persistence.saved_search import SavedSearchService


@dataclass
class ExportDocument:
    """A subject's exported data."""

    subject: str
    sessions: list[dict] = field(default_factory=list)
    saved_searches: list[dict] = field(default_factory=list)
    audit_entries: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "sessions": self.sessions,
            "saved_searches": self.saved_searches,
            "audit_entries": self.audit_entries,
        }


@dataclass
class PurgeResult:
    """Summary of a purge operation."""

    subject: str
    sessions_removed: int
    saved_searches_removed: int


class DataRightsService:
    """Implements data export and purge for a subject."""

    def __init__(
        self,
        *,
        sessions: SessionStore,
        saved_searches: SavedSearchService,
        audit: AuditLog,
    ) -> None:
        self._sessions = sessions
        self._saved = saved_searches
        self._audit = audit

    async def export(self, subject: str) -> ExportDocument:
        """Collect all data held about a subject."""
        doc = ExportDocument(subject=subject)

        session = self._sessions.get(subject)
        if session is not None:
            doc.sessions = [
                {"query": t.query, "language": t.plan.detected_language, "ts": t.ts}
                for t in session.turns
            ]

        saved = await self._saved.list_by_owner(subject)
        doc.saved_searches = [
            {"id": s.id, "query": s.query, "label": s.label} for s in saved
        ]

        doc.audit_entries = [
            {
                "seq": e.seq,
                "action": e.action,
                "resource": e.resource,
                "outcome": e.outcome,
                "ts": e.ts,
            }
            for e in self._audit.entries(actor=subject)
        ]
        return doc

    async def purge(self, subject: str) -> PurgeResult:
        """Delete a subject's sessions and saved searches."""
        sessions_removed = 1 if self._sessions.drop(subject) else 0
        saved = await self._saved.list_by_owner(subject)
        for s in saved:
            await self._saved.delete(subject, s.id)
        return PurgeResult(
            subject=subject,
            sessions_removed=sessions_removed,
            saved_searches_removed=len(saved),
        )
