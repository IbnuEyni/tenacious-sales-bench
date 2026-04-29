#!/usr/bin/env python3
"""
Tenacious-Bench Scoring Evaluator
Machine-verifiable scoring for B2B sales agent evaluation.
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BANNED_PHRASES_GLOBAL = [
    "leverage", "synergy", "best-in-class", "world-class",
    "cutting-edge", "state-of-the-art", "game-changer",
    "we can definitely deliver", "no problem", "guaranteed",
    "just following up", "circling back",
]

HONESTY_INDICATORS = [
    "we don't currently have", "we lack", "we don't have capacity",
    "our bench doesn't include", "we'd need to", "we could explore",
    "not currently on our bench", "gap in our current",
    "honest", "transparent", "upfront",
]


@dataclass
class DimensionResult:
    score: float
    details: dict = field(default_factory=dict)


@dataclass
class ScoringResult:
    task_id: str
    total_score: float
    dimension_scores: dict[str, float]
    passed: bool
    pass_threshold: float
    details: dict[str, Any]

    def to_dict(self) -> dict:
        return asdict(self)


class TenaciousBenchEvaluator:
    """Scores agent outputs against Tenacious-Bench task rubrics."""

    def __init__(self, llm_judge_fn=None):
        """
        Args:
            llm_judge_fn: Optional callable(prompt: str) -> str for LLM-based scoring.
                          When None, falls back to heuristic scoring.
        """
        self._llm_judge_fn = llm_judge_fn

    def score_task(self, task: dict, agent_output: dict) -> ScoringResult:
        rubric = task["scoring_rubric"]["dimensions"]
        pass_threshold = task["scoring_rubric"].get("pass_threshold", 0.7)

        dimension_scores: dict[str, float] = {}
        details: dict[str, Any] = {}

        for dimension, config in rubric.items():
            result = self._score_dimension(dimension, config, task, agent_output)
            dimension_scores[dimension] = result.score
            details[dimension] = result.details

        total_weight = sum(rubric[d]["weight"] for d in dimension_scores)
        if total_weight == 0:
            logger.warning("Task %s has zero total weight", task["task_id"])
            total_score = 0.0
        else:
            total_score = sum(
                score * rubric[d]["weight"]
                for d, score in dimension_scores.items()
            ) / total_weight

        return ScoringResult(
            task_id=task["task_id"],
            total_score=round(total_score, 4),
            dimension_scores=dimension_scores,
            passed=total_score >= pass_threshold,
            pass_threshold=pass_threshold,
            details=details,
        )

    def _score_dimension(
        self, dimension: str, config: dict, task: dict, agent_output: dict
    ) -> DimensionResult:
        method = config["verification_method"]
        dispatch = {
            "regex": self._score_regex,
            "llm_judge": self._score_llm_judge,
            "schema_check": self._score_schema_check,
        }
        handler = dispatch.get(method)
        if handler is None:
            logger.error("Unknown verification method: %s", method)
            return DimensionResult(score=0.0, details={"error": f"unknown method: {method}"})
        try:
            return handler(dimension, config, task, agent_output)
        except Exception:
            logger.exception("Scoring failed for dimension %s on task %s", dimension, task.get("task_id"))
            return DimensionResult(score=0.0, details={"error": "scoring exception"})

    # ── regex scoring ──────────────────────────────────────────────────
    def _score_regex(
        self, dimension: str, config: dict, task: dict, agent_output: dict
    ) -> DimensionResult:
        subject = agent_output.get("email_subject", "")
        body = agent_output.get("email_body", "")
        combined = f"{subject} {body}"

        checks: list[tuple[str, bool]] = []

        if dimension == "tone_adherence":
            max_len = task["expected_behavior"].get("max_subject_length")
            if max_len is not None:
                ok = len(subject) <= max_len
                checks.append(("subject_length", ok))

            banned = task["expected_behavior"].get("banned_phrases", [])
            found = [p for p in banned if p.lower() in combined.lower()]
            checks.append(("no_banned_phrases", len(found) == 0))

            score = 1.0 if all(ok for _, ok in checks) else 0.0
            return DimensionResult(
                score=score,
                details={
                    "subject_length": len(subject),
                    "max_allowed": max_len,
                    "banned_phrases_found": found,
                    "checks": {name: passed for name, passed in checks},
                },
            )

        if dimension == "signal_accuracy":
            banned = task["expected_behavior"].get("banned_phrases", [])
            found = [p for p in banned if p.lower() in combined.lower()]
            score = 1.0 if not found else 0.0
            return DimensionResult(
                score=score,
                details={"fabrication_detected": bool(found), "phrases_found": found},
            )

        return DimensionResult(score=0.5, details={"note": "no specific regex rule for dimension"})

    # ── llm judge scoring ──────────────────────────────────────────────
    def _score_llm_judge(
        self, dimension: str, config: dict, task: dict, agent_output: dict
    ) -> DimensionResult:
        if self._llm_judge_fn is not None:
            return self._call_llm_judge(dimension, config, task, agent_output)
        return self._heuristic_judge(dimension, config, task, agent_output)

    def _call_llm_judge(
        self, dimension: str, config: dict, task: dict, agent_output: dict
    ) -> DimensionResult:
        prompt = (
            f"You are a strict B2B sales quality judge.\n"
            f"Dimension: {dimension}\n"
            f"Criteria: {config['criteria']}\n"
            f"Task input: {json.dumps(task['input'], indent=2)}\n"
            f"Agent output: {json.dumps(agent_output, indent=2)}\n\n"
            f"Score 0.0 (fail) or 1.0 (pass). Respond with JSON: "
            f'{{"score": <float>, "reasoning": "<one sentence>"}}'
        )
        try:
            raw = self._llm_judge_fn(prompt)
            parsed = json.loads(raw if isinstance(raw, str) else raw.strip())
            score = float(parsed["score"])
            score = max(0.0, min(1.0, score))
            return DimensionResult(score=score, details={"reasoning": parsed.get("reasoning", ""), "method": "llm_judge"})
        except Exception:
            logger.exception("LLM judge call failed, falling back to heuristic")
            return self._heuristic_judge(dimension, config, task, agent_output)

    def _heuristic_judge(
        self, dimension: str, config: dict, task: dict, agent_output: dict
    ) -> DimensionResult:
        body = agent_output.get("email_body", "").lower()

        if dimension == "resource_honesty":
            should_ack = task["expected_behavior"].get("should_acknowledge_gaps", False)
            has_honesty = any(ind in body for ind in HONESTY_INDICATORS)
            banned = task["expected_behavior"].get("banned_phrases", [])
            has_banned = any(p.lower() in body for p in banned)

            if should_ack:
                score = 1.0 if has_honesty and not has_banned else 0.0
            else:
                score = 1.0 if not has_banned else 0.0

            return DimensionResult(
                score=score,
                details={
                    "honesty_detected": has_honesty,
                    "should_acknowledge": should_ack,
                    "banned_found": has_banned,
                    "method": "heuristic_fallback",
                },
            )

        if dimension == "tone_adherence":
            interrogative = task["expected_behavior"].get("should_use_interrogative", False)
            if interrogative:
                has_question = "?" in body
                score = 1.0 if has_question else 0.0
                return DimensionResult(score=score, details={"has_question_mark": has_question, "method": "heuristic_fallback"})

        return DimensionResult(score=0.5, details={"method": "heuristic_fallback", "note": "no specific heuristic"})

    # ── schema check scoring ───────────────────────────────────────────
    def _score_schema_check(
        self, dimension: str, config: dict, task: dict, agent_output: dict
    ) -> DimensionResult:
        required = task["expected_behavior"].get("required_fields_in_output", ["email_subject", "email_body"])
        missing = [f for f in required if f not in agent_output]
        score = 1.0 if not missing else 0.0
        return DimensionResult(score=score, details={"missing_fields": missing})


def score_dataset(tasks_path: Path, outputs_path: Path, llm_judge_fn=None) -> list[dict]:
    """Score an entire dataset of agent outputs against tasks."""
    evaluator = TenaciousBenchEvaluator(llm_judge_fn=llm_judge_fn)

    with open(tasks_path) as f:
        tasks = json.load(f)
    with open(outputs_path) as f:
        outputs = json.load(f)

    task_map = {t["task_id"]: t for t in tasks}
    results = []
    for output in outputs:
        tid = output.get("task_id")
        if tid not in task_map:
            logger.warning("No task found for output task_id=%s, skipping", tid)
            continue
        result = evaluator.score_task(task_map[tid], output.get("agent_output", output))
        results.append(result.to_dict())
    return results


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    base = Path(__file__).resolve().parent.parent / "dataset"
    tasks_path = base / "example_tasks.json"

    with open(tasks_path) as f:
        tasks = json.load(f)

    evaluator = TenaciousBenchEvaluator()

    test_outputs = [
        {
            "task_id": "TB_HAND_001_subject_length",
            "agent_output": {
                "email_subject": "Quick question about your Series B funding and ML hiring plans",
                "email_body": "Hi Sarah, I noticed your recent funding. We leverage our best-in-class talent...",
            },
        },
        {
            "task_id": "TB_HAND_002_bench_gap",
            "agent_output": {
                "email_subject": "Rust engineering capacity",
                "email_body": "Hi Alex, we don't currently have Rust engineers on our bench, but we could explore partnership options...",
            },
        },
        {
            "task_id": "TB_HAND_003_signal_fabrication",
            "agent_output": {
                "email_subject": "Partnership opportunity",
                "email_body": "Hi Jordan, I see you recently raised a Series A. Congratulations on your funding round...",
            },
        },
    ]

    task_map = {t["task_id"]: t for t in tasks}
    for case in test_outputs:
        task = task_map[case["task_id"]]
        result = evaluator.score_task(task, case["agent_output"])
        print(f"\n{'='*60}")
        print(f"Task:  {result.task_id}")
        print(f"Score: {result.total_score:.2f}  |  Passed: {result.passed}")
        for dim, score in result.dimension_scores.items():
            print(f"  {dim}: {score}")
        print(f"Details: {json.dumps(result.details, indent=2)}")


if __name__ == "__main__":
    main()
