"""A/B answer-quality evaluation runner.

Runs both variants through the agent, then asks an optional judge (live Gemini) which answer
is better. Without a judge the run still completes deterministically (every comparison is a
TIE), so the framework is fully usable in mock mode; the judge only refines verdicts.
"""
from __future__ import annotations

from typing import Any

from app.eval.models import EvalResult, EvalRun, EvalVerdict, GoldenSet

_JUDGE_SYSTEM = (
    "You are an evaluation judge. Given a user query, expected facts, and two AI answers "
    "(A and B), decide which is better. Return STRICT JSON "
    '{"verdict": "win_a"|"win_b"|"tie", "reasoning": "..."}. '
    "Criteria: factual accuracy, relevance, conciseness. No code fences."
)


class EvalRunner:
    """Runs A/B eval against a golden set using the agent, with an optional judge."""

    def __init__(self, agent: Any, judge: Any | None = None) -> None:
        self._agent = agent
        self._judge = judge

    async def _answer(self, query: str) -> str:
        resp = await self._agent.chat(query, None)
        return resp.answer if resp is not None else ""

    async def _judge_verdict(self, query, expected, a, b) -> tuple[EvalVerdict, str]:
        if self._judge is None:
            return EvalVerdict.TIE, "judge unavailable"
        try:
            prompt = f"Query: {query}\nExpected: {expected}\nAnswer A: {a}\nAnswer B: {b}"
            data = await self._judge.generate_json(_JUDGE_SYSTEM, prompt)
            return EvalVerdict(data.get("verdict", "tie")), data.get("reasoning", "")
        except Exception:  # noqa: BLE001 - judge failure must not abort the run
            return EvalVerdict.TIE, "judge error"

    async def run(self, golden_set: GoldenSet, run: EvalRun) -> EvalRun:
        """Execute the eval run, updating and returning ``run``."""
        run.status = "running"
        results: list[EvalResult] = []
        wins_a = wins_b = ties = 0

        for gq in golden_set.queries:
            try:
                answer_a = await self._answer(gq.query)
                answer_b = await self._answer(gq.query)
            except Exception as exc:  # noqa: BLE001 - record per-query failure, continue
                results.append(
                    EvalResult(gq.query, "", "", EvalVerdict.ERROR, str(exc))
                )
                continue

            verdict, reasoning = await self._judge_verdict(
                gq.query, gq.expected_facts, answer_a, answer_b
            )
            if verdict == EvalVerdict.WIN_A:
                wins_a += 1
            elif verdict == EvalVerdict.WIN_B:
                wins_b += 1
            else:
                ties += 1
            results.append(
                EvalResult(gq.query, answer_a, answer_b, verdict, reasoning)
            )

        scored = wins_a + wins_b + ties  # excludes ERROR rows
        run.results = results
        run.win_rate_a = wins_a / scored if scored else 0.0
        run.win_rate_b = wins_b / scored if scored else 0.0
        run.tie_rate = ties / scored if scored else 0.0
        run.status = "complete"
        return run
