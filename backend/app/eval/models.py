"""Evaluation domain models for A/B answer-quality runs."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class EvalVerdict(str, Enum):
    WIN_A = "win_a"
    WIN_B = "win_b"
    TIE = "tie"
    ERROR = "error"


@dataclass
class GoldenQuery:
    """A golden test query with optional expected facts."""

    query: str
    expected_facts: list[str] = field(default_factory=list)


@dataclass
class GoldenSet:
    """A named collection of golden queries."""

    set_id: str
    name: str
    queries: list[GoldenQuery] = field(default_factory=list)


@dataclass
class EvalResult:
    """Per-query A/B result."""

    query: str
    answer_a: str
    answer_b: str
    verdict: EvalVerdict
    judge_reasoning: str = ""


@dataclass
class EvalRun:
    """Result of a full evaluation run."""

    run_id: str
    model_a: str
    model_b: str
    golden_set_id: str
    status: Literal["pending", "running", "complete", "error"] = "pending"
    results: list[EvalResult] = field(default_factory=list)
    win_rate_a: float = 0.0
    win_rate_b: float = 0.0
    tie_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "model_a": self.model_a,
            "model_b": self.model_b,
            "golden_set_id": self.golden_set_id,
            "status": self.status,
            "win_rate_a": round(self.win_rate_a, 4),
            "win_rate_b": round(self.win_rate_b, 4),
            "tie_rate": round(self.tie_rate, 4),
            "results": [
                {
                    "query": r.query,
                    "verdict": r.verdict.value,
                    "judge_reasoning": r.judge_reasoning,
                }
                for r in self.results
            ],
        }
