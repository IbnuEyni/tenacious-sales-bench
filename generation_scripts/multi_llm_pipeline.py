#!/usr/bin/env python3
"""
multi_llm_pipeline.py — Runnable Multi-LLM Synthesis Pipeline
==============================================================
Implements the routing table documented in generation_scripts/README.md.

This script is the authoritative implementation of:
  1. Model routing: generation model family ≠ judge model family (Li et al., 2025)
  2. Judge filter: three-axis quality scoring with explicit threshold (mean ≥ 3.5/5.0)
  3. Pairwise dedup: n-gram + Jaccard similarity checks before any task is accepted
  4. Seed control: deterministic random state for reproducible candidate selection

Usage
-----
  # Dry-run (no API calls, uses existing batch files as candidates):
  python3 generation_scripts/multi_llm_pipeline.py --dry-run

  # Full run (requires OPENROUTER_API_KEY env var):
  python3 generation_scripts/multi_llm_pipeline.py --batch 1
  python3 generation_scripts/multi_llm_pipeline.py --batch 2
  python3 generation_scripts/multi_llm_pipeline.py --batch 3

Environment variables
---------------------
  OPENROUTER_API_KEY   Required for live generation/judging (omit for dry-run)
  PIPELINE_SEED        Random seed (default: 42)
"""

import argparse
import hashlib
import json
import logging
import os
import random
import re
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Seed control ──────────────────────────────────────────────────────────────
_SEED: list[int] = [int(os.environ.get("PIPELINE_SEED", "42"))]
random.seed(_SEED[0])


def get_seed() -> int:
    return _SEED[0]


def set_seed(value: int) -> None:
    _SEED[0] = value
    random.seed(value)

# ── Model routing table ───────────────────────────────────────────────────────
# Generation model family ≠ judge model family (hard rule — Li et al., 2025).
# Qwen family is reserved exclusively for judging; never used for generation.
ROUTING_TABLE: dict[int, dict] = {
    1: {
        "generation_model": "anthropic/claude-sonnet-4-5",
        "judge_model":      "qwen/qwen3-235b-a22b",
        "probe_focus":      ["4.4", "7.1", "7.2", "4.2", "4.1", "4.3", "5.1", "3.3"],
        "description":      "Adversarial personas, emoji probe, agent self-monitoring",
    },
    2: {
        "generation_model": "anthropic/claude-sonnet-4-5",
        "judge_model":      "qwen/qwen3-235b-a22b",
        "probe_focus":      ["3.3", "7.2", "5.2", "3.1", "3.2", "2.1", "9.3", "9.1", "2.4", "2.3"],
        "description":      "Bench changes mid-conversation, wrong seniority, pricing edge cases",
    },
    3: {
        "generation_model": "openai/gpt-4.1",
        "judge_model":      "qwen/qwen3-235b-a22b",
        "probe_focus":      ["7.1", "4.2", "8.1", "3.2", "8.2"],
        "description":      "Legal/cultural/booking edge cases",
    },
}

# ── Judge filter configuration ────────────────────────────────────────────────
# Three scoring dimensions, each 1–5. Task included only if mean ≥ JUDGE_THRESHOLD.
JUDGE_DIMENSIONS: list[dict] = [
    {
        "name":        "input_coherence",
        "description": "Is the prospect scenario internally consistent? (1=contradictory, 5=fully coherent)",
    },
    {
        "name":        "ground_truth_verifiability",
        "description": "Can a human unambiguously determine pass/fail from expected_behavior? (1=ambiguous, 5=crystal clear)",
    },
    {
        "name":        "rubric_clarity",
        "description": "Are the scoring criteria specific enough to apply consistently? (1=vague, 5=precise)",
    },
]
JUDGE_THRESHOLD: float = 3.5   # mean score across all three dimensions
JUDGE_MIN_SCORE: float = 1.0   # per-dimension floor
JUDGE_MAX_SCORE: float = 5.0   # per-dimension ceiling

# ── Pairwise dedup configuration ──────────────────────────────────────────────
NGRAM_SIZE: int = 10            # 10-gram (relaxed from Chen et al.'s 8-gram — see memo 03)
JACCARD_THRESHOLD: float = 0.85 # similarity above this → duplicate
JACCARD_MIN_TOKENS: int = 8     # skip dedup for very sparse signal briefs

PIPELINE_SEED = property(get_seed)  # backwards-compatible alias for documentation


# ── Dedup helpers ─────────────────────────────────────────────────────────────

def _discriminative_text(task: dict) -> str:
    """Extract only the fields that determine correct answer (not shared templates).

    Operates on signal_brief + bench_state + expected_behavior to avoid flagging
    tasks that share domain vocabulary in conversation_history templates.
    """
    parts = []
    sb = task.get("input", {}).get("signal_brief", {})
    if sb:
        parts.append(json.dumps(sb, sort_keys=True))
    bs = task.get("input", {}).get("bench_state", {})
    if bs:
        parts.append(json.dumps(bs, sort_keys=True))
    eb = task.get("expected_behavior", {})
    if eb:
        parts.append(json.dumps(eb, sort_keys=True))
    return " ".join(parts).lower()


def _ngrams(text: str, n: int) -> set[str]:
    tokens = text.split()
    if len(tokens) < n:
        return set()
    return {" ".join(tokens[i:i+n]) for i in range(len(tokens) - n + 1)}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_duplicate(candidate: dict, existing_tasks: list[dict]) -> tuple[bool, str]:
    """Pairwise dedup check: n-gram overlap + Jaccard similarity.

    Returns (is_dup, reason_string). Checks every existing task against the
    candidate — O(n) per candidate, acceptable at our dataset scale (≤300 tasks).
    """
    cand_text = _discriminative_text(candidate)
    cand_tokens = set(cand_text.split())
    cand_ngrams = _ngrams(cand_text, NGRAM_SIZE)

    if len(cand_tokens) < JACCARD_MIN_TOKENS:
        return False, "skipped (sparse signal brief)"

    for existing in existing_tasks:
        ex_text = _discriminative_text(existing)
        ex_ngrams = _ngrams(ex_text, NGRAM_SIZE)

        # Stage 1: n-gram overlap
        shared = cand_ngrams & ex_ngrams
        if shared:
            return True, (
                f"n-gram overlap with {existing['task_id']}: "
                f"{len(shared)} shared {NGRAM_SIZE}-gram(s): {list(shared)[:2]}"
            )

        # Stage 2: Jaccard similarity
        ex_tokens = set(ex_text.split())
        sim = _jaccard(cand_tokens, ex_tokens)
        if sim >= JACCARD_THRESHOLD:
            return True, (
                f"Jaccard similarity {sim:.3f} ≥ {JACCARD_THRESHOLD} "
                f"with {existing['task_id']}"
            )

    return False, ""


# ── Judge filter ──────────────────────────────────────────────────────────────

def build_judge_prompt(task: dict) -> str:
    """Build a rubric-anchored judge prompt for quality filtering.

    Passes all three JUDGE_DIMENSIONS explicitly to anchor the judge's scoring
    rather than asking for open-ended quality assessment (Gu et al., 2024).
    """
    dims_text = "\n".join(
        f"  {i+1}. {d['name']}: {d['description']}"
        for i, d in enumerate(JUDGE_DIMENSIONS)
    )
    return (
        f"You are a strict benchmark quality judge for B2B sales agent evaluation tasks.\n\n"
        f"Score the following task on each dimension from {JUDGE_MIN_SCORE:.0f} to {JUDGE_MAX_SCORE:.0f}:\n"
        f"{dims_text}\n\n"
        f"Task:\n{json.dumps(task, indent=2)}\n\n"
        f"Respond with JSON only:\n"
        f'{{"input_coherence": <1-5>, "ground_truth_verifiability": <1-5>, '
        f'"rubric_clarity": <1-5>, "reasoning": "<one sentence>"}}'
    )


def parse_judge_response(raw: str) -> Optional[dict]:
    """Parse judge JSON response, tolerating minor formatting issues."""
    try:
        # Strip markdown code fences if present
        cleaned = re.sub(r"```(?:json)?|```", "", raw).strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return None


def judge_task(task: dict, judge_model: str, api_key: str) -> tuple[bool, float, str]:
    """Call the judge model and apply the threshold filter.

    Returns (passes_filter, mean_score, reasoning).
    On API failure, conservatively rejects the task (fail-safe default).
    """
    try:
        import urllib.request
        prompt = build_judge_prompt(task)
        payload = json.dumps({
            "model": judge_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.0,
        }).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
        raw = body["choices"][0]["message"]["content"]
        parsed = parse_judge_response(raw)
        if parsed is None:
            logger.warning("Judge response unparseable: %s", raw[:100])
            return False, 0.0, "parse_error"

        scores = [
            max(JUDGE_MIN_SCORE, min(JUDGE_MAX_SCORE, float(parsed.get(d["name"], 0))))
            for d in JUDGE_DIMENSIONS
        ]
        mean = sum(scores) / len(scores)
        passes = mean >= JUDGE_THRESHOLD
        return passes, round(mean, 2), parsed.get("reasoning", "")

    except Exception as exc:
        logger.error("Judge API call failed: %s — rejecting task conservatively", exc)
        return False, 0.0, f"api_error: {exc}"


# ── Pipeline orchestrator ─────────────────────────────────────────────────────

def run_pipeline(batch: int, dry_run: bool = False) -> dict:
    """Run the full synthesis pipeline for a given batch number.

    Steps:
      1. Load candidate tasks from the pre-generated batch file
      2. Load all existing accepted tasks for dedup comparison
      3. For each candidate: dedup check → judge filter → accept/reject
      4. Write accepted tasks back to the batch output file
      5. Return a summary report

    In dry-run mode, skips API calls and uses a mock judge that accepts all tasks
    with a fixed score of 4.0 — useful for testing the pipeline logic locally.
    """
    route = ROUTING_TABLE[batch]
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not dry_run and not api_key:
        logger.error("OPENROUTER_API_KEY not set. Use --dry-run or set the env var.")
        sys.exit(1)

    repo_root = Path(__file__).resolve().parent.parent
    batch_file = repo_root / "dataset" / f"synthesis_batch{batch}_tasks.json"

    if not batch_file.exists():
        logger.error("Batch file not found: %s", batch_file)
        sys.exit(1)

    with open(batch_file) as f:
        candidates: list[dict] = json.load(f)
    logger.info("Loaded %d candidates from %s", len(candidates), batch_file.name)

    # Load all existing tasks for pairwise dedup
    existing: list[dict] = []
    for json_file in sorted((repo_root / "dataset").glob("*.json")):
        if json_file.name in ("schema.json", "contamination_check.json"):
            continue
        try:
            data = json.load(open(json_file))
            if isinstance(data, list):
                existing.extend(data)
        except (json.JSONDecodeError, OSError):
            pass
    logger.info("Loaded %d existing tasks for dedup comparison", len(existing))

    # Shuffle candidates with seeded RNG for reproducible ordering
    rng = random.Random(get_seed())
    rng.shuffle(candidates)

    accepted, rejected_dedup, rejected_judge = [], [], []

    for task in candidates:
        # ── Stage 1: pairwise dedup ──
        is_dup, dup_reason = is_duplicate(task, existing + accepted)
        if is_dup:
            rejected_dedup.append({"task_id": task["task_id"], "reason": dup_reason})
            logger.debug("DEDUP REJECT %s: %s", task["task_id"], dup_reason)
            continue

        # ── Stage 2: judge filter ──
        if dry_run:
            passes, mean_score, reasoning = True, 4.0, "dry-run mock score"
        else:
            passes, mean_score, reasoning = judge_task(task, route["judge_model"], api_key)

        task.setdefault("metadata", {})
        task["metadata"]["generation_model"] = route["generation_model"]
        task["metadata"]["judge_model"] = route["judge_model"]
        task["metadata"]["judge_score"] = mean_score

        if passes:
            accepted.append(task)
            logger.info("ACCEPT %s (judge=%.2f)", task["task_id"], mean_score)
        else:
            rejected_judge.append({
                "task_id": task["task_id"],
                "judge_score": mean_score,
                "reasoning": reasoning,
                "resolution": "dropped — below quality threshold",
            })
            logger.info("JUDGE REJECT %s (score=%.2f < %.2f): %s",
                        task["task_id"], mean_score, JUDGE_THRESHOLD, reasoning)

    # Write accepted tasks back
    with open(batch_file, "w") as f:
        json.dump(accepted, f, indent=2)

    summary = {
        "batch": batch,
        "seed": get_seed(),
        "generation_model": route["generation_model"],
        "judge_model": route["judge_model"],
        "judge_threshold": JUDGE_THRESHOLD,
        "candidates": len(candidates),
        "accepted": len(accepted),
        "rejected_dedup": len(rejected_dedup),
        "rejected_judge": len(rejected_judge),
        "rejection_rate_dedup": round(len(rejected_dedup) / max(len(candidates), 1), 3),
        "rejection_rate_judge": round(len(rejected_judge) / max(len(candidates) - len(rejected_dedup), 1), 3),
        "dedup_details": rejected_dedup,
        "judge_details": rejected_judge,
    }

    report_path = repo_root / "dataset" / f"pipeline_report_batch{batch}.json"
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info("Pipeline report written to %s", report_path)

    return summary


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Multi-LLM synthesis pipeline")
    parser.add_argument("--batch", type=int, choices=[1, 2, 3], default=1,
                        help="Synthesis batch to process (1, 2, or 3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip API calls; use mock judge scores (for testing)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed (default: 42 or $PIPELINE_SEED)")
    args = parser.parse_args()

    if args.seed is not None:
        set_seed(args.seed)

    summary = run_pipeline(batch=args.batch, dry_run=args.dry_run)

    print(f"\n{'='*60}")
    print(f"Batch {summary['batch']} pipeline complete (seed={summary['seed']})")
    print(f"  Generation model : {summary['generation_model']}")
    print(f"  Judge model      : {summary['judge_model']}")
    print(f"  Judge threshold  : {summary['judge_threshold']}")
    print(f"  Candidates       : {summary['candidates']}")
    print(f"  Accepted         : {summary['accepted']}")
    print(f"  Rejected (dedup) : {summary['rejected_dedup']} ({summary['rejection_rate_dedup']:.1%})")
    print(f"  Rejected (judge) : {summary['rejected_judge']} ({summary['rejection_rate_judge']:.1%})")
    if summary["judge_details"]:
        print(f"\n  Judge rejections:")
        for r in summary["judge_details"]:
            print(f"    {r['task_id']}: score={r['judge_score']:.2f} — {r['reasoning']}")
            print(f"      Resolution: {r['resolution']}")


if __name__ == "__main__":
    main()
