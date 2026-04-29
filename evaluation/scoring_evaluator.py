#!/usr/bin/env python3
"""
Tenacious-Bench Scoring Evaluator
==================================
Machine-verifiable scoring for B2B sales agent evaluation tasks.

Architecture
------------
TenaciousBenchEvaluator.score_task()
    └── _score_dimension()          dispatches per verification_method
            ├── _score_regex()      hard constraints: subject length, banned phrases,
            │                       fabrication detection — deterministic, zero LLM cost
            ├── _score_llm_judge()  semantic dimensions: resource_honesty,
            │                       workflow_correctness — requires understanding of
            │                       valid surface forms
            │       ├── _call_llm_judge()   when llm_judge_fn is provided
            │       └── _heuristic_judge()  fallback when no LLM is available
            └── _score_schema_check()  structural validation: required output fields

Rubric application
------------------
Each task's scoring_rubric.dimensions maps dimension names to:
  - weight:               contribution to total_score (must sum to 1.0)
  - criteria:             natural-language description passed to LLM judge
  - verification_method:  "regex" | "llm_judge" | "schema_check"

Total score = Σ(dimension_score × weight) / Σ(weights)
Task passes when total_score >= pass_threshold (default 0.7).

Hybrid design rationale (Gu et al., 2024)
------------------------------------------
Dimensions with hard constraints (tone_adherence, signal_accuracy) use regex:
  - subject length ≤ 60 chars is binary — an LLM judge adds variance with no benefit
  - banned phrase detection is a string match — regex is faster, cheaper, and more reliable

Dimensions requiring semantic understanding (resource_honesty, workflow_correctness)
use llm_judge:
  - "acknowledges bench gap" has many valid surface forms; no finite regex list covers them
  - "qualifies before booking" requires multi-step reasoning about conversation structure
"""

import json
import logging
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

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
    """Scores agent outputs against Tenacious-Bench task rubrics.

    Usage
    -----
    evaluator = TenaciousBenchEvaluator()                        # heuristic fallback
    evaluator = TenaciousBenchEvaluator(llm_judge_fn=my_fn)     # with LLM judge

    result = evaluator.score_task(task, agent_output)
    print(result.total_score, result.passed)
    """

    def __init__(self, llm_judge_fn: Optional[Callable[[str], str]] = None):
        """
        Args:
            llm_judge_fn: Optional callable(prompt: str) -> str for LLM-based scoring.
                          Prompt is a structured rubric-anchored judge prompt.
                          Expected response: JSON string {"score": float, "reasoning": str}
                          When None, falls back to heuristic scoring for llm_judge dimensions.
        """
        self._llm_judge_fn = llm_judge_fn

    def score_task(self, task: dict, agent_output: dict) -> ScoringResult:
        """Score a single agent output against a task rubric.

        Args:
            task:         A validated Tenacious-Bench task dict (schema v0.2).
            agent_output: Dict with at minimum {"email_subject": str, "email_body": str}.
                          May include additional fields checked by schema_check dimensions.

        Returns:
            ScoringResult with total_score, per-dimension scores, pass/fail, and details.
        """
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
        """Dispatch to the correct scoring handler based on verification_method.

        Falls back to a 0.0 score (not 0.5) on unknown methods to avoid silently
        inflating scores for misconfigured tasks.
        """
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
            logger.exception(
                "Scoring failed for dimension %s on task %s", dimension, task.get("task_id")
            )
            return DimensionResult(score=0.0, details={"error": "scoring exception"})

    # ── regex scoring ──────────────────────────────────────────────────────────
    def _score_regex(
        self, dimension: str, config: dict, task: dict, agent_output: dict
    ) -> DimensionResult:
        """Apply deterministic regex/string checks for hard-constraint dimensions.

        Rubric application:
          tone_adherence:  subject length ≤ max_subject_length AND no banned phrases
          signal_accuracy: no fabrication phrases present in output
          workflow_correctness (regex): checks required_fields_in_output presence
          All other dimensions: logged warning, score 0.0 (explicit failure, not silent 0.5)

        This method is the right tool when the pass/fail criterion is unambiguous and
        expressible as a string constraint. It is intentionally not used for dimensions
        where valid outputs have many surface forms (resource_honesty, workflow_correctness
        semantic checks) — those route to _score_llm_judge.
        """
        subject = agent_output.get("email_subject", "")
        body = agent_output.get("email_body", "")
        combined = f"{subject} {body}"

        if dimension == "tone_adherence":
            return self._check_tone_adherence(task, subject, combined)

        if dimension == "signal_accuracy":
            return self._check_signal_accuracy(task, combined)

        if dimension == "workflow_correctness":
            # Regex-mode workflow check: verify required structural fields are present.
            # Semantic workflow correctness (qualification, hierarchy) must use llm_judge.
            required = task["expected_behavior"].get("required_fields_in_output", [])
            missing = [f for f in required if f not in agent_output]
            score = 1.0 if not missing else 0.0
            return DimensionResult(
                score=score,
                details={
                    "missing_required_fields": missing,
                    "note": "structural check only — semantic workflow correctness requires llm_judge",
                },
            )

        if dimension == "resource_honesty":
            # resource_honesty via regex: check banned phrases only (no semantic honesty check).
            # Full resource_honesty evaluation requires llm_judge.
            banned = task["expected_behavior"].get("banned_phrases", [])
            found = [p for p in banned if p.lower() in combined.lower()]
            score = 1.0 if not found else 0.0
            return DimensionResult(
                score=score,
                details={
                    "banned_phrases_found": found,
                    "note": "banned-phrase check only — honesty detection requires llm_judge",
                },
            )

        logger.warning(
            "No regex rule for dimension '%s' on task %s — scoring 0.0",
            dimension, task.get("task_id"),
        )
        return DimensionResult(
            score=0.0,
            details={"error": f"no regex rule for dimension '{dimension}'"},
        )

    def _check_tone_adherence(
        self, task: dict, subject: str, combined: str
    ) -> DimensionResult:
        """Tone adherence rubric: subject length + banned phrase checks.

        Both checks must pass for score=1.0. Either failure → score=0.0.
        This is intentionally strict: a subject that is 1 char over the limit
        is a real failure (Gmail mobile truncation) regardless of content quality.
        """
        checks: list[tuple[str, bool]] = []

        max_len = task["expected_behavior"].get("max_subject_length")
        if max_len is not None:
            checks.append(("subject_length_ok", len(subject) <= max_len))

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

    def _check_signal_accuracy(self, task: dict, combined: str) -> DimensionResult:
        """Signal accuracy rubric: detect fabrication phrases in agent output.

        Banned phrases for signal_accuracy tasks are fabrication patterns —
        e.g., "you recently raised", "your Series A" — that should not appear
        when funding_detected=False in the signal brief.
        """
        banned = task["expected_behavior"].get("banned_phrases", [])
        found = [p for p in banned if p.lower() in combined.lower()]
        score = 1.0 if not found else 0.0
        return DimensionResult(
            score=score,
            details={"fabrication_detected": bool(found), "phrases_found": found},
        )

    # ── llm judge scoring ──────────────────────────────────────────────────────
    def _score_llm_judge(
        self, dimension: str, config: dict, task: dict, agent_output: dict
    ) -> DimensionResult:
        """Route to LLM judge or heuristic fallback.

        When llm_judge_fn is provided, constructs a rubric-anchored prompt (Gu et al., 2024)
        that passes the dimension criteria directly — reducing judge variance by 15-30%
        compared to open-ended quality prompts.

        When llm_judge_fn is None (development/offline mode), falls back to heuristic_judge
        which covers resource_honesty and basic tone_adherence with keyword matching.
        The heuristic is explicitly insufficient for hard workflow_correctness tasks —
        see _heuristic_judge docstring.
        """
        if self._llm_judge_fn is not None:
            return self._call_llm_judge(dimension, config, task, agent_output)
        return self._heuristic_judge(dimension, config, task, agent_output)

    def _call_llm_judge(
        self, dimension: str, config: dict, task: dict, agent_output: dict
    ) -> DimensionResult:
        """Call the external LLM judge with a rubric-anchored prompt.

        Prompt structure follows Gu et al. (2024) rubric-anchored design:
          - Dimension name and criteria are explicit in the prompt
          - Task input context is included for grounding
          - Response format is constrained to JSON {score, reasoning}

        On parse failure or exception, falls back to heuristic to avoid hard failures
        during evaluation runs.
        """
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
            score = max(0.0, min(1.0, float(parsed["score"])))
            return DimensionResult(
                score=score,
                details={"reasoning": parsed.get("reasoning", ""), "method": "llm_judge"},
            )
        except Exception:
            logger.exception("LLM judge call failed, falling back to heuristic")
            return self._heuristic_judge(dimension, config, task, agent_output)

    def _heuristic_judge(
        self, dimension: str, config: dict, task: dict, agent_output: dict
    ) -> DimensionResult:
        """Heuristic fallback for llm_judge dimensions when no LLM is available.

        Coverage and known limitations:
          resource_honesty:    keyword matching against HONESTY_INDICATORS + banned phrases.
                               Reliable for clear cases ("we don't currently have Rust").
                               May miss valid honesty expressions not in the indicator list.

          tone_adherence:      checks for interrogative phrasing when should_use_interrogative
                               is True. Falls back to 0.5 (uncertain) for other tone checks
                               that require semantic understanding — this is intentional and
                               documented, not a silent failure.

          workflow_correctness: returns 0.5 (uncertain) for all cases. This dimension requires
                               multi-step semantic reasoning (qualification sequences, hierarchy
                               respect) that keyword matching cannot approximate. The 0.5 score
                               signals "judge required" rather than "probably passing."
                               This is the primary motivation for training the SimPO judge.

          All other dimensions: returns 0.5 (uncertain) with explicit note.
        """
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
                return DimensionResult(
                    score=score,
                    details={"has_question_mark": has_question, "method": "heuristic_fallback"},
                )
            # Tone adherence without a specific interrogative check requires semantic
            # understanding of style guide compliance — heuristic cannot assess this.
            return DimensionResult(
                score=0.5,
                details={
                    "method": "heuristic_fallback",
                    "note": "tone_adherence without interrogative check requires llm_judge",
                },
            )

        if dimension == "workflow_correctness":
            # Workflow correctness requires semantic reasoning about qualification sequences,
            # decision-maker hierarchy, and booking protocols. Keyword matching is insufficient.
            # Score 0.5 explicitly signals "LLM judge required" — not "probably passing."
            return DimensionResult(
                score=0.5,
                details={
                    "method": "heuristic_fallback",
                    "note": (
                        "workflow_correctness requires llm_judge for reliable scoring. "
                        "0.5 = uncertain, not passing. Train SimPO judge (Act IV) to resolve."
                    ),
                },
            )

        return DimensionResult(
            score=0.5,
            details={"method": "heuristic_fallback", "note": f"no heuristic for '{dimension}'"},
        )

    # ── schema check scoring ───────────────────────────────────────────────────
    def _score_schema_check(
        self, dimension: str, config: dict, task: dict, agent_output: dict
    ) -> DimensionResult:
        """Structural validation: verify required output fields are present.

        Rubric application: checks that agent_output contains all fields listed in
        expected_behavior.required_fields_in_output. Defaults to ["email_subject", "email_body"]
        if not specified — every task output must have at minimum these two fields.

        This is a prerequisite check, not a quality check. A task that fails schema_check
        cannot be meaningfully scored on other dimensions.
        """
        required = task["expected_behavior"].get(
            "required_fields_in_output", ["email_subject", "email_body"]
        )
        missing = [f for f in required if f not in agent_output]
        score = 1.0 if not missing else 0.0
        return DimensionResult(score=score, details={"missing_fields": missing})


_ALLOWED_ROOTS = (
    Path(__file__).resolve().parent.parent / "dataset",
    Path(__file__).resolve().parent.parent / "tenacious_bench_v0.1",
)


def _safe_open(path: Path) -> Path:
    """Resolve path and verify it sits inside an allowed root (CWE-22 guard)."""
    resolved = path.resolve()
    if not any(resolved.is_relative_to(root) for root in _ALLOWED_ROOTS):
        raise ValueError(
            f"Path '{resolved}' is outside allowed dataset directories. "
            "Only paths under dataset/ or tenacious_bench_v0.1/ are permitted."
        )
    return resolved


def score_dataset(
    tasks_path: Path,
    outputs_path: Path,
    llm_judge_fn: Optional[Callable[[str], str]] = None,
) -> list[dict]:
    """Score an entire dataset of agent outputs against tasks.

    Args:
        tasks_path:    Path to a JSON file containing a list of task dicts.
                       Must be inside dataset/ or tenacious_bench_v0.1/.
        outputs_path:  Path to a JSON file containing a list of output dicts,
                       each with {"task_id": str, "agent_output": dict}.
                       Must be inside dataset/ or tenacious_bench_v0.1/.
        llm_judge_fn:  Optional LLM judge callable. See TenaciousBenchEvaluator.

    Returns:
        List of ScoringResult dicts, one per matched output.
        Outputs with no matching task_id are skipped with a warning.

    Raises:
        ValueError: If either path resolves outside the allowed dataset directories.
    """
    evaluator = TenaciousBenchEvaluator(llm_judge_fn=llm_judge_fn)

    with open(_safe_open(tasks_path)) as f:
        tasks = json.load(f)
    with open(_safe_open(outputs_path)) as f:
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

    # Three test cases covering all three example task types:
    # TB_HAND_001: tone_adherence (regex) — subject length + banned phrases
    # TB_HAND_002: resource_honesty (llm_judge/heuristic) — bench gap acknowledgment
    # TB_HAND_003: signal_accuracy (regex) — fabrication detection
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
