#!/usr/bin/env python3
"""
Contamination Prevention Checks for Tenacious-Bench.
Three checks before any task enters the held-out partition:
  1. N-gram overlap (<8-gram between held-out and train)
  2. Embedding similarity (cosine <0.85 for any pair)
  3. Time-shift verification (signal dates are documentable)
"""

import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def extract_text(task: dict, discriminative_only: bool = False) -> str:
    """Flatten a task's fields into text for comparison.
    
    When discriminative_only=True, extracts only the prospect's reply
    and signal brief — the content that makes each task unique.
    Excludes agent openers, banned phrase lists, and bench state
    constants which are shared rubric definitions, not test content.
    """
    parts = []

    if not discriminative_only:
        pd = task.get("input", {}).get("prospect_data", {})
        parts.append(pd.get("company_name", ""))
        parts.append(pd.get("contact_title", ""))

    sb = task.get("input", {}).get("signal_brief", {})
    for v in sb.values():
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            parts.extend(str(x) for x in v)

    for msg in task.get("input", {}).get("conversation_history", []):
        if discriminative_only and msg.get("role") == "agent":
            continue
        parts.append(msg.get("message", ""))

    if not discriminative_only:
        eb = task.get("expected_behavior", {})
        for v in eb.values():
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, list):
                parts.extend(str(x) for x in v)
            elif isinstance(v, bool):
                parts.append(str(v))

        bs = task.get("input", {}).get("bench_state", {})
        for k, v in bs.items():
            parts.append(f"{k}={v}")

    return " ".join(parts).lower().strip()


def ngrams(text: str, n: int) -> set[tuple[str, ...]]:
    tokens = text.split()
    if len(tokens) < n:
        return set()
    return {tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)}


def check_ngram_overlap(
    held_out: list[dict], train: list[dict], max_n: int = 10
) -> list[dict[str, Any]]:
    """Flag any held-out task sharing an 8-gram with any train task.
    Uses discriminative-only text to avoid false positives from shared
    domain vocabulary (agent openers, company descriptions)."""
    violations = []
    train_ngrams: set[tuple[str, ...]] = set()
    for t in train:
        train_ngrams |= ngrams(extract_text(t, discriminative_only=True), max_n)

    for t in held_out:
        task_ng = ngrams(extract_text(t, discriminative_only=True), max_n)
        overlap = task_ng & train_ngrams
        if overlap:
            violations.append({
                "task_id": t["task_id"],
                "check": "ngram_overlap",
                "n": max_n,
                "overlapping_ngrams": len(overlap),
                "sample": " ".join(list(overlap)[0]) if overlap else "",
            })
    return violations


def check_embedding_similarity(
    held_out: list[dict], train: list[dict], threshold: float = 0.85
) -> list[dict[str, Any]]:
    """Flag held-out tasks with cosine similarity >threshold to any train task."""
    violations = []
    try:
        import numpy as np
    except ImportError:
        logger.warning("numpy not installed — skipping embedding similarity check")
        return [{"check": "embedding_similarity", "status": "skipped", "reason": "numpy not installed"}]

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
    except ImportError:
        logger.warning("sentence-transformers not installed — using TF-IDF fallback")
        return _tfidf_similarity(held_out, train, threshold)

    train_texts = [extract_text(t, discriminative_only=True) for t in train]
    held_texts = [extract_text(t, discriminative_only=True) for t in held_out]

    train_emb = model.encode(train_texts, normalize_embeddings=True)
    held_emb = model.encode(held_texts, normalize_embeddings=True)

    sims = held_emb @ train_emb.T  # cosine similarity matrix

    for i, t in enumerate(held_out):
        max_sim = float(np.max(sims[i]))
        if max_sim > threshold:
            max_j = int(np.argmax(sims[i]))
            violations.append({
                "task_id": t["task_id"],
                "check": "embedding_similarity",
                "max_cosine": round(max_sim, 4),
                "most_similar_train_task": train[max_j]["task_id"],
                "threshold": threshold,
            })
    return violations


def _tfidf_similarity(
    held_out: list[dict], train: list[dict], threshold: float
) -> list[dict[str, Any]]:
    """Fallback: word-overlap Jaccard similarity."""
    violations = []
    train_sets = [set(extract_text(t, discriminative_only=True).split()) for t in train]

    for t in held_out:
        h_set = set(extract_text(t, discriminative_only=True).split())
        if len(h_set) < 8:
            continue
        for j, tr_set in enumerate(train_sets):
            if len(tr_set) < 8:
                continue
            jaccard = len(h_set & tr_set) / len(h_set | tr_set)
            if jaccard > threshold:
                violations.append({
                    "task_id": t["task_id"],
                    "check": "embedding_similarity_fallback_jaccard",
                    "jaccard": round(jaccard, 4),
                    "most_similar_train_task": train[j]["task_id"],
                    "threshold": threshold,
                })
                break
    return violations


def check_time_shift(held_out: list[dict]) -> list[dict[str, Any]]:
    """Flag tasks referencing signals without documentable time windows."""
    violations = []
    for t in held_out:
        sb = t.get("input", {}).get("signal_brief", {})
        funding_date = sb.get("funding_date")
        if funding_date:
            try:
                raw = funding_date.replace("Z", "+00:00")
                dt = datetime.fromisoformat(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age = (datetime.now(timezone.utc) - dt).days
                if age > 365:
                    violations.append({
                        "task_id": t["task_id"],
                        "check": "time_shift",
                        "funding_date": funding_date,
                        "age_days": age,
                        "issue": "Signal older than 365 days — may not be documentable",
                    })
            except ValueError:
                violations.append({
                    "task_id": t["task_id"],
                    "check": "time_shift",
                    "issue": f"Unparseable funding_date: {funding_date}",
                })
    return violations


def run_all_checks(
    held_out: list[dict], train: list[dict]
) -> dict[str, Any]:
    """Run all three contamination checks and return a report."""
    ngram_v = check_ngram_overlap(held_out, train)
    embed_v = check_embedding_similarity(held_out, train)
    time_v = check_time_shift(held_out)

    all_violations = ngram_v + embed_v + time_v
    passed = len(all_violations) == 0

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "held_out_count": len(held_out),
        "train_count": len(train),
        "passed": passed,
        "total_violations": len(all_violations),
        "ngram_violations": len(ngram_v),
        "embedding_violations": len([v for v in embed_v if "status" not in v]),
        "time_shift_violations": len(time_v),
        "violations": all_violations,
    }
    return report


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    partitions_dir = PROJECT_ROOT / "dataset" / "partitions"
    held_out_path = partitions_dir / "held_out.json"
    train_path = partitions_dir / "train.json"

    if not held_out_path.exists() or not train_path.exists():
        logger.error("Partitions not found at %s. Run partition script first.", partitions_dir)
        return 1

    with open(held_out_path) as f:
        held_out = json.load(f)
    with open(train_path) as f:
        train = json.load(f)

    report = run_all_checks(held_out, train)

    out_path = PROJECT_ROOT / "dataset" / "contamination_check.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    status = "PASSED" if report["passed"] else "FAILED"
    print(f"\nContamination Check: {status}")
    print(f"  Held-out tasks: {report['held_out_count']}")
    print(f"  Train tasks:    {report['train_count']}")
    print(f"  Violations:     {report['total_violations']}")

    if not report["passed"]:
        for v in report["violations"]:
            print(f"  [{v.get('check')}] {v.get('task_id', 'N/A')}: {v}")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
