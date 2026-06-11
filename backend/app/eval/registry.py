"""In-memory registry of golden sets and eval runs."""
from __future__ import annotations

import uuid

from app.eval.models import EvalRun, GoldenSet


class EvalRegistry:
    """Stores golden sets and eval-run results."""

    def __init__(self) -> None:
        self._golden_sets: dict[str, GoldenSet] = {}
        self._runs: dict[str, EvalRun] = {}

    def register_golden_set(self, gs: GoldenSet) -> None:
        self._golden_sets[gs.set_id] = gs

    def get_golden_set(self, set_id: str) -> GoldenSet | None:
        return self._golden_sets.get(set_id)

    def all_golden_sets(self) -> list[GoldenSet]:
        return list(self._golden_sets.values())

    def create_run(self, model_a: str, model_b: str, golden_set_id: str) -> EvalRun:
        run = EvalRun(
            run_id=uuid.uuid4().hex[:12],
            model_a=model_a,
            model_b=model_b,
            golden_set_id=golden_set_id,
        )
        self._runs[run.run_id] = run
        return run

    def get_run(self, run_id: str) -> EvalRun | None:
        return self._runs.get(run_id)

    def update_run(self, run: EvalRun) -> None:
        self._runs[run.run_id] = run
