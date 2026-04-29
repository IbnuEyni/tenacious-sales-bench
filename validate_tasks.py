#!/usr/bin/env python3
"""
Task Validation for Tenacious-Bench.
Validates all tasks against schema and quality invariants.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any

import jsonschema

logger = logging.getLogger(__name__)

VALID_PROBES = frozenset(
    f"{cat}.{num}"
    for cat, nums in {
        1: range(1, 6), 2: range(1, 5), 3: range(1, 4),
        4: range(1, 6), 5: range(1, 3), 6: range(1, 4),
        7: range(1, 3), 8: range(1, 4), 9: range(1, 4),
        10: range(1, 4),
    }.items()
    for num in nums
)

CATEGORY_REQUIRED_FIELDS: dict[str, list[str]] = {
    "tone_consistency": ["max_subject_length"],
    "resource_honesty": ["should_acknowledge_gaps"],
}

PROJECT_ROOT = Path(__file__).resolve().parent


def _safe_path(raw: str) -> Path:
    """Resolve path and ensure it stays within the project root."""
    resolved = (PROJECT_ROOT / raw).resolve()
    if not str(resolved).startswith(str(PROJECT_ROOT)):
        raise ValueError(f"Path escapes project root: {raw}")
    return resolved


class TaskValidator:
    def __init__(self, schema_path: str = "dataset/schema.json"):
        safe = _safe_path(schema_path)
        with open(safe) as f:
            self.schema = json.load(f)

    def validate_task(self, task: dict[str, Any]) -> tuple[bool, list[str]]:
        errors: list[str] = []

        try:
            jsonschema.validate(task, self.schema)
        except jsonschema.ValidationError as exc:
            errors.append(f"Schema: {exc.message}")

        errors.extend(self._quality_checks(task))
        return len(errors) == 0, errors

    def _quality_checks(self, task: dict[str, Any]) -> list[str]:
        errors: list[str] = []

        # Rubric weight sum
        dims = task.get("scoring_rubric", {}).get("dimensions", {})
        total_w = sum(d.get("weight", 0) for d in dims.values())
        if abs(total_w - 1.0) > 0.01:
            errors.append(f"Weights sum to {total_w:.3f}, expected ~1.0")

        # Category-specific required fields
        cat = task.get("category", "")
        expected = task.get("expected_behavior", {})
        for field in CATEGORY_REQUIRED_FIELDS.get(cat, []):
            if field not in expected:
                errors.append(f"{cat} tasks must specify expected_behavior.{field}")

        # Probe ID validity
        for pid in task.get("probe_ids", []):
            if pid not in VALID_PROBES:
                errors.append(f"Invalid probe_id: {pid}")

        return errors

    def validate_dataset(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        seen_ids: set[str] = set()
        duplicate_ids: list[str] = []
        valid = 0
        invalid = 0
        errors_by_task: dict[str, list[str]] = {}
        cats: dict[str, int] = {}
        diffs: dict[str, int] = {}
        modes: dict[str, int] = {}

        for task in tasks:
            tid = task.get("task_id", "unknown")

            # Uniqueness check
            if tid in seen_ids:
                duplicate_ids.append(tid)
            seen_ids.add(tid)

            ok, errs = self.validate_task(task)
            if ok:
                valid += 1
            else:
                invalid += 1
                errors_by_task[tid] = errs

            cats[task.get("category", "?")] = cats.get(task.get("category", "?"), 0) + 1
            diffs[task.get("difficulty", "?")] = diffs.get(task.get("difficulty", "?"), 0) + 1
            modes[task.get("source_mode", "?")] = modes.get(task.get("source_mode", "?"), 0) + 1

        return {
            "total_tasks": len(tasks),
            "valid_tasks": valid,
            "invalid_tasks": invalid,
            "duplicate_ids": duplicate_ids,
            "errors_by_task": errors_by_task,
            "category_distribution": cats,
            "difficulty_distribution": diffs,
            "source_mode_distribution": modes,
        }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    validator = TaskValidator()

    task_files = [
        "dataset/example_tasks.json",
        "dataset/programmatic_tasks.json",
        "dataset/prospect_response_tasks.json",
        "dataset/enrichment_tasks.json",
        "dataset/pipeline_stage_tasks.json",
        "dataset/gap_outreach_tasks.json",
        "dataset/trace_derived_tasks.json",
        "dataset/synthesis_batch1_tasks.json",
        "dataset/synthesis_batch2_tasks.json",
        "dataset/synthesis_batch3_tasks.json",
        "dataset/final_40_tasks.json",
    ]
    all_tasks: list[dict] = []

    for rel in task_files:
        path = _safe_path(rel)
        if not path.exists():
            logger.warning("File not found: %s", path)
            continue
        with open(path) as f:
            loaded = json.load(f)
        all_tasks.extend(loaded)
        logger.info("Loaded %d tasks from %s", len(loaded), rel)

    if not all_tasks:
        logger.error("No tasks to validate")
        return 1

    results = validator.validate_dataset(all_tasks)

    print(f"\n{'='*50}")
    print(f"VALIDATION SUMMARY")
    print(f"{'='*50}")
    print(f"Total:   {results['total_tasks']}")
    print(f"Valid:   {results['valid_tasks']}")
    print(f"Invalid: {results['invalid_tasks']}")

    if results["duplicate_ids"]:
        print(f"\nDUPLICATE IDs: {results['duplicate_ids']}")

    if results["invalid_tasks"]:
        print(f"\nERRORS:")
        for tid, errs in results["errors_by_task"].items():
            for e in errs:
                print(f"  [{tid}] {e}")

    print(f"\nDistributions:")
    print(f"  Categories:  {results['category_distribution']}")
    print(f"  Difficulty:  {results['difficulty_distribution']}")
    print(f"  Source mode: {results['source_mode_distribution']}")

    target = 250
    pct = results["total_tasks"] / target * 100
    print(f"\nProgress: {results['total_tasks']}/{target} tasks ({pct:.1f}%)")

    return 0 if results["invalid_tasks"] == 0 and not results["duplicate_ids"] else 1


if __name__ == "__main__":
    sys.exit(main())
