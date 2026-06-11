"""Tests for the saved-search alerter."""
from __future__ import annotations

import asyncio

import pytest

from app.notifications.saved_search_alerter import AlertSnapshot, SavedSearchAlerter


class _Saved:
    def __init__(self, searches):
        self._searches = searches

    async def list_all_searches(self):
        return self._searches


class _Search:
    def __init__(self, sid, owner, query):
        self.id, self.owner, self.query = sid, owner, query


class _Event:
    def __init__(self, eid, open_now=True):
        self.id, self.open_now = eid, open_now


class _Result:
    def __init__(self, event):
        self.event = event


class _Response:
    def __init__(self, ids, open_flags=None):
        flags = open_flags or [True] * len(ids)
        self.results = [_Result(_Event(i, o)) for i, o in zip(ids, flags)]


class _Agent:
    def __init__(self, responses, fail=False):
        # responses: list of id-lists, one per poll cycle
        self._responses = responses
        self._call = 0
        self._fail = fail

    async def search(self, query, loc, k, sess, cursor):
        if self._fail:
            raise RuntimeError("search boom")
        idx = min(self._call, len(self._responses) - 1)
        self._call += 1
        return _Response(self._responses[idx])


class _Dispatcher:
    def __init__(self):
        self.calls = []

    async def dispatch(self, event_name, tenant, payload):
        self.calls.append((event_name, payload))
        return []


async def test_first_cycle_baselines_no_alert():
    saved = _Saved([_Search("s1", "o1", "halal")])
    agent = _Agent([["a", "b"]])
    disp = _Dispatcher()
    alerter = SavedSearchAlerter(saved, agent, disp)
    fired = await alerter.poll_once()
    assert fired == 0
    assert disp.calls == []


async def test_new_open_result_fires_within_two_cycles():
    saved = _Saved([_Search("s1", "o1", "halal")])
    # cycle 1: {a}; cycle 2: {a, b} -> b is new -> alert
    agent = _Agent([["a"], ["a", "b"]])
    disp = _Dispatcher()
    alerter = SavedSearchAlerter(saved, agent, disp)
    await alerter.poll_once()         # baseline
    fired = await alerter.poll_once() # diff -> fire
    assert fired == 1
    assert disp.calls[0][0] == "saved_search.alert"
    assert disp.calls[0][1]["new_open"] == ["b"]


async def test_no_alert_when_unchanged():
    saved = _Saved([_Search("s1", "o1", "halal")])
    agent = _Agent([["a"], ["a"]])
    disp = _Dispatcher()
    alerter = SavedSearchAlerter(saved, agent, disp)
    await alerter.poll_once()
    fired = await alerter.poll_once()
    assert fired == 0


async def test_closed_results_excluded():
    saved = _Saved([_Search("s1", "o1", "halal")])
    agent = _Agent([[]])  # baseline empty
    # Inject a closed venue on cycle 2 via a custom response.
    disp = _Dispatcher()
    alerter = SavedSearchAlerter(saved, agent, disp)
    await alerter.poll_once()
    # Manually craft a response where the only new id is closed.
    class _A2:
        async def search(self, *a):
            return _Response(["c"], open_flags=[False])
    alerter._agent = _A2()
    fired = await alerter.poll_once()
    assert fired == 0  # closed venue does not trigger


async def test_agent_failure_skips_search():
    saved = _Saved([_Search("s1", "o1", "halal")])
    alerter = SavedSearchAlerter(saved, _Agent([["a"]], fail=True), _Dispatcher())
    fired = await alerter.poll_once()
    assert fired == 0


async def test_start_and_stop_lifecycle():
    saved = _Saved([])
    alerter = SavedSearchAlerter(saved, _Agent([[]]), _Dispatcher(), poll_interval_s=0.01)
    await alerter.start()
    assert alerter._task is not None
    await asyncio.sleep(0.02)
    await alerter.stop()
    assert alerter._task is None


def test_snapshot_dataclass():
    snap = AlertSnapshot("s1", "o1")
    assert snap.result_ids == set()
