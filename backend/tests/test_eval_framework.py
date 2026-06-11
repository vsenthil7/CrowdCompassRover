"""Tests for the A/B answer-quality evaluation framework."""
from __future__ import annotations

import pytest

from app.eval.models import EvalRun, EvalVerdict, GoldenQuery, GoldenSet
from app.eval.registry import EvalRegistry
from app.eval.runner import EvalRunner


class _StubAgent:
    """Returns a fixed answer; optionally raises to exercise the error path."""

    def __init__(self, answer="an answer", fail=False):
        self._answer = answer
        self._fail = fail

    async def chat(self, query, location, **kw):
        if self._fail:
            raise RuntimeError("agent boom")
        return type("R", (), {"answer": f"{self._answer}:{query}"})()


class _FakeJudge:
    def __init__(self, verdict="win_a", reasoning="A is better", fail=False):
        self._verdict = verdict
        self._reasoning = reasoning
        self._fail = fail

    async def generate_json(self, system, prompt):
        if self._fail:
            raise RuntimeError("judge boom")
        return {"verdict": self._verdict, "reasoning": self._reasoning}


def _set():
    return GoldenSet("gs1", "Smoke", [GoldenQuery("halal food"), GoldenQuery("stadium route")])


# --- registry ---

def test_registry_golden_set_crud():
    reg = EvalRegistry()
    reg.register_golden_set(_set())
    assert reg.get_golden_set("gs1").name == "Smoke"
    assert len(reg.all_golden_sets()) == 1
    assert reg.get_golden_set("missing") is None


def test_registry_run_lifecycle():
    reg = EvalRegistry()
    run = reg.create_run("m-a", "m-b", "gs1")
    assert reg.get_run(run.run_id) is run
    run.status = "complete"
    reg.update_run(run)
    assert reg.get_run(run.run_id).status == "complete"


# --- runner ---

async def test_runner_without_judge_all_tie():
    run = EvalRun("r1", "a", "b", "gs1")
    out = await EvalRunner(_StubAgent()).run(_set(), run)
    assert out.status == "complete"
    assert out.tie_rate == 1.0
    assert out.win_rate_a == 0.0
    assert all(r.verdict is EvalVerdict.TIE for r in out.results)


async def test_runner_with_judge_win_a():
    run = EvalRun("r2", "a", "b", "gs1")
    out = await EvalRunner(_StubAgent(), judge=_FakeJudge("win_a")).run(_set(), run)
    assert out.win_rate_a == 1.0
    assert out.results[0].judge_reasoning == "A is better"


async def test_runner_with_judge_win_b():
    run = EvalRun("r3", "a", "b", "gs1")
    out = await EvalRunner(_StubAgent(), judge=_FakeJudge("win_b")).run(_set(), run)
    assert out.win_rate_b == 1.0


async def test_runner_judge_failure_falls_back_to_tie():
    run = EvalRun("r4", "a", "b", "gs1")
    out = await EvalRunner(_StubAgent(), judge=_FakeJudge(fail=True)).run(_set(), run)
    assert out.tie_rate == 1.0
    assert out.results[0].judge_reasoning == "judge error"


async def test_runner_agent_error_records_error_row():
    run = EvalRun("r5", "a", "b", "gs1")
    out = await EvalRunner(_StubAgent(fail=True)).run(_set(), run)
    assert all(r.verdict is EvalVerdict.ERROR for r in out.results)
    # All rows errored -> no scored comparisons -> rates are zero.
    assert out.win_rate_a == 0.0 and out.tie_rate == 0.0


async def test_runner_empty_set():
    run = EvalRun("r6", "a", "b", "gs-empty")
    out = await EvalRunner(_StubAgent()).run(GoldenSet("gs-empty", "Empty", []), run)
    assert out.status == "complete"
    assert out.win_rate_a == 0.0


def test_run_to_dict():
    run = EvalRun("r7", "m-a", "m-b", "gs1")
    run.win_rate_a = 0.6666666
    d = run.to_dict()
    assert d["run_id"] == "r7"
    assert d["win_rate_a"] == 0.6667
    assert d["results"] == []
