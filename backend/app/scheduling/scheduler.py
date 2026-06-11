"""A minimal async interval scheduler for periodic jobs (e.g. ingestion refresh).

Runs registered jobs on fixed intervals in a background task. Designed for testability:
the loop body is exposed as ``run_due`` so tests can drive ticks deterministically without
real time or sleeping, while ``start``/``stop`` manage the live asyncio task.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Awaitable, Callable

from app.observability.logging_config import get_logger, log_event

_logger = get_logger("scheduler")

JobFn = Callable[[], Awaitable[None]]


@dataclass
class _Job:
    name: str
    interval: float
    fn: JobFn
    next_run: float


class Scheduler:
    """Interval-based async job scheduler."""

    def __init__(self, *, clock: Callable[[], float] = time.monotonic) -> None:
        self._jobs: list[_Job] = []
        self._clock = clock
        self._task: asyncio.Task | None = None
        self._stopped = asyncio.Event()

    def every(self, name: str, interval: float, fn: JobFn) -> None:
        """Register a job to run every ``interval`` seconds."""
        self._jobs.append(_Job(name, interval, fn, self._clock() + interval))

    async def run_due(self) -> int:
        """Run all jobs whose next_run has elapsed; return how many ran."""
        now = self._clock()
        ran = 0
        for job in self._jobs:
            if now >= job.next_run:
                try:
                    await job.fn()
                except Exception as exc:  # noqa: BLE001 - isolate job failures
                    log_event(_logger, logging.ERROR, "job_failed", job=job.name, error=str(exc))
                job.next_run = now + job.interval
                ran += 1
        return ran

    async def _loop(self, poll: float) -> None:  # pragma: no cover - exercised via start/stop
        while not self._stopped.is_set():
            await self.run_due()
            try:
                await asyncio.wait_for(self._stopped.wait(), timeout=poll)
            except asyncio.TimeoutError:
                pass

    def start(self, poll: float = 1.0) -> None:
        """Start the background loop."""
        if self._task is None:
            self._stopped.clear()
            self._task = asyncio.create_task(self._loop(poll))

    async def stop(self) -> None:
        """Stop the background loop and await its completion."""
        self._stopped.set()
        if self._task is not None:
            await self._task
            self._task = None

    @property
    def job_count(self) -> int:
        """Number of registered jobs."""
        return len(self._jobs)
