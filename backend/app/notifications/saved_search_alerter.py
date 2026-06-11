"""Saved-search alert poller.

Re-runs each saved search, diffs the currently-open result set against the last snapshot,
and dispatches a ``saved_search.alert`` webhook when new open venues appear. The core
``poll_once`` is synchronous-to-await and side-effect-contained so it is fully testable
without a running loop; ``start``/``stop`` wrap it in a background task for production.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.observability.logging_config import get_logger

_logger = get_logger("alerts.saved_search")


@dataclass
class AlertSnapshot:
    """Last-seen open result IDs for a saved search."""

    search_id: str
    owner: str
    result_ids: set[str] = field(default_factory=set)


class SavedSearchAlerter:
    """Polls saved searches and fires alerts on new open_now matches."""

    def __init__(
        self,
        saved_search_service,
        agent,
        webhook_dispatcher,
        *,
        poll_interval_s: float = 120.0,
    ) -> None:
        self._saved = saved_search_service
        self._agent = agent
        self._dispatcher = webhook_dispatcher
        self._interval = poll_interval_s
        self._snapshots: dict[str, AlertSnapshot] = {}
        self._running = False
        self._task: asyncio.Task | None = None

    async def poll_once(self) -> int:
        """Run one poll cycle. Returns the number of searches that fired an alert."""
        searches = await self._saved.list_all_searches()
        fired = 0
        for s in searches:
            try:
                response = await self._agent.search(s.query, None, 20, None, None)
                current_ids = {r.event.id for r in response.results if r.event.open_now}
            except Exception:  # noqa: BLE001 - one bad search must not stop the cycle
                continue

            snapshot = self._snapshots.get(s.id)
            if snapshot is None:
                # First sighting: record baseline, do not alert.
                self._snapshots[s.id] = AlertSnapshot(s.id, s.owner, current_ids)
                continue

            new_open = current_ids - snapshot.result_ids
            if new_open:
                fired += 1
                _logger.info("alert: %d new open results for search %s", len(new_open), s.id)
                await self._dispatcher.dispatch(
                    "saved_search.alert",
                    "default",
                    {"search_id": s.id, "owner": s.owner, "new_open": sorted(new_open)},
                )
            snapshot.result_ids = current_ids
        return fired

    async def _loop(self) -> None:  # pragma: no cover - exercised via start/stop in real run
        while self._running:
            try:
                await self.poll_once()
            except Exception:  # noqa: BLE001
                _logger.exception("alert poll cycle failed")
            await asyncio.sleep(self._interval)

    async def start(self) -> None:
        """Start the background poll loop."""
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Stop the background poll loop."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
