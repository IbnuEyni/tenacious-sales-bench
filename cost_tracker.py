#!/usr/bin/env python3
"""
Cost Tracking for Week 11 Tenacious-Bench.
Budget: $10 total across 4 buckets.
"""

import json
import logging
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BUDGET_TOTAL = 10.0
BUCKET_LIMITS: dict[str, float] = {
    "dataset_authoring": 5.0,
    "training": 5.0,
    "evaluation": 3.0,
    "reserve": 2.0,
}


@dataclass(frozen=True)
class CostEntry:
    timestamp: str
    bucket: str
    service: str
    amount_usd: float
    purpose: str
    model_or_resource: str


class CostTracker:
    def __init__(self, log_path: Path | str = "cost_log.json", budget_usd: float = BUDGET_TOTAL):
        self._path = Path(log_path).resolve()
        self._budget = budget_usd
        self._lock = threading.Lock()
        self._entries: list[CostEntry] = self._load()

    def _load(self) -> list[CostEntry]:
        if not self._path.exists():
            return []
        with open(self._path) as f:
            return [CostEntry(**e) for e in json.load(f)]

    def _save(self) -> None:
        with open(self._path, "w") as f:
            json.dump([asdict(e) for e in self._entries], f, indent=2)

    def log(self, bucket: str, service: str, amount_usd: float,
            purpose: str, model_or_resource: str) -> dict[str, Any]:
        if bucket not in BUCKET_LIMITS:
            raise ValueError(f"Invalid bucket '{bucket}'. Valid: {list(BUCKET_LIMITS)}")
        if amount_usd <= 0:
            raise ValueError("amount_usd must be positive")

        entry = CostEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            bucket=bucket,
            service=service,
            amount_usd=round(amount_usd, 6),
            purpose=purpose,
            model_or_resource=model_or_resource,
        )

        with self._lock:
            self._entries.append(entry)
            self._save()

        summary = self.summary()
        bucket_spent = summary["by_bucket"].get(bucket, 0)
        bucket_limit = BUCKET_LIMITS[bucket]

        if summary["remaining"] < 0:
            logger.warning("BUDGET EXCEEDED: spent $%.4f / $%.2f", summary["total_spent"], self._budget)
        if bucket_spent > bucket_limit:
            logger.warning("Bucket '%s' over limit: $%.4f / $%.2f", bucket, bucket_spent, bucket_limit)

        logger.info(
            "Cost: $%.4f (%s) | Total: $%.4f / $%.2f | Remaining: $%.4f",
            amount_usd, bucket, summary["total_spent"], self._budget, summary["remaining"],
        )
        return summary

    def summary(self) -> dict[str, Any]:
        with self._lock:
            total = sum(e.amount_usd for e in self._entries)
            by_bucket: dict[str, float] = {}
            for e in self._entries:
                by_bucket[e.bucket] = by_bucket.get(e.bucket, 0) + e.amount_usd
            return {
                "total_spent": round(total, 6),
                "budget": self._budget,
                "remaining": round(self._budget - total, 6),
                "by_bucket": {k: round(v, 6) for k, v in by_bucket.items()},
                "entry_count": len(self._entries),
            }

    def print_summary(self) -> None:
        s = self.summary()
        print(f"\n{'='*40}")
        print(f"COST SUMMARY")
        print(f"{'='*40}")
        print(f"Spent:     ${s['total_spent']:.4f} / ${s['budget']:.2f}")
        print(f"Remaining: ${s['remaining']:.4f}")
        for bucket, amount in s["by_bucket"].items():
            limit = BUCKET_LIMITS.get(bucket, 0)
            print(f"  {bucket}: ${amount:.4f} / ${limit:.2f}")


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    tracker = CostTracker()
    tracker.print_summary()


if __name__ == "__main__":
    main()
