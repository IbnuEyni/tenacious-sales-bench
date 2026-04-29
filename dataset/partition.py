#!/usr/bin/env python3
"""
Dataset Partitioner for Tenacious-Bench.
Splits tasks into train (50%), dev (30%), held-out (20%) with stratification.
"""

import json
import logging
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SEED = 42
SPLIT_RATIOS = {"train": 0.50, "dev": 0.30, "held_out": 0.20}
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def stratified_split(
    tasks: list[dict], ratios: dict[str, float], seed: int = SEED
) -> dict[str, list[dict]]:
    """Split tasks with stratification by category and difficulty."""
    rng = random.Random(seed)

    # Group by (category, difficulty)
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in tasks:
        key = (t.get("category", "?"), t.get("difficulty", "?"))
        groups[key].append(t)

    splits: dict[str, list[dict]] = {name: [] for name in ratios}

    for key, group in groups.items():
        rng.shuffle(group)
        n = len(group)
        boundaries = {}
        cumulative = 0
        for name, ratio in ratios.items():
            start = cumulative
            cumulative += int(round(n * ratio))
            boundaries[name] = (start, min(cumulative, n))

        # Ensure last split gets any remainder
        last_name = list(ratios.keys())[-1]
        boundaries[last_name] = (boundaries[last_name][0], n)

        for name, (start, end) in boundaries.items():
            splits[name].extend(group[start:end])

    return splits


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    dataset_dir = PROJECT_ROOT / "dataset"
    task_files = [
        "example_tasks.json",
        "programmatic_tasks.json",
        "prospect_response_tasks.json",
        "enrichment_tasks.json",
        "pipeline_stage_tasks.json",
        "gap_outreach_tasks.json",
        "trace_derived_tasks.json",
        "synthesis_batch1_tasks.json",
        "synthesis_batch2_tasks.json",
        "synthesis_batch3_tasks.json",
        "final_40_tasks.json",
    ]

    all_tasks: list[dict] = []
    for fname in task_files:
        path = dataset_dir / fname
        if not path.exists():
            logger.warning("Not found: %s", path)
            continue
        with open(path) as f:
            loaded = json.load(f)
        all_tasks.extend(loaded)
        logger.info("Loaded %d tasks from %s", len(loaded), fname)

    if not all_tasks:
        logger.error("No tasks found")
        return 1

    # Check for duplicate IDs
    ids = [t["task_id"] for t in all_tasks]
    dupes = [tid for tid, cnt in defaultdict(int, {tid: ids.count(tid) for tid in set(ids)}).items() if cnt > 1]
    if dupes:
        logger.error("Duplicate task IDs found: %s", dupes)
        return 1

    splits = stratified_split(all_tasks, SPLIT_RATIOS)

    # Save partitions
    partitions_dir = dataset_dir / "partitions"
    partitions_dir.mkdir(exist_ok=True)

    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "total_tasks": len(all_tasks),
        "ratios": SPLIT_RATIOS,
        "splits": {},
    }

    for name, tasks in splits.items():
        out_path = partitions_dir / f"{name}.json"
        with open(out_path, "w") as f:
            json.dump(tasks, f, indent=2)

        cats = defaultdict(int)
        diffs = defaultdict(int)
        for t in tasks:
            cats[t.get("category", "?")] += 1
            diffs[t.get("difficulty", "?")] += 1

        manifest["splits"][name] = {
            "count": len(tasks),
            "categories": dict(cats),
            "difficulties": dict(diffs),
        }
        logger.info("  %s: %d tasks", name, len(tasks))

    manifest_path = partitions_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nPartitioned {len(all_tasks)} tasks (seed={SEED}):")
    for name, info in manifest["splits"].items():
        print(f"  {name:10s}: {info['count']:3d} tasks  {info['categories']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
