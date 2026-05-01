#!/usr/bin/env python3
"""
Compute Delta A, B, C Ablations
=================================
Takes score files from baseline, trained judge, and prompted judge.
Runs paired bootstrap (10,000 resamples) for statistical significance.
Outputs ablation_results.json.

Run locally (no GPU needed — just reads score files):
  python3 ablations/compute_deltas.py
"""

import json
import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOOTSTRAP_SAMPLES = 10_000
SEED = 42


def paired_bootstrap(scores_a: list[float], scores_b: list[float],
                     n_samples: int = BOOTSTRAP_SAMPLES,
                     seed: int = SEED) -> dict:
    """
    Paired bootstrap test: is mean(scores_b) - mean(scores_a) > 0?

    Returns:
      delta:      observed mean difference (b - a)
      ci_lower:   2.5th percentile of bootstrap distribution
      ci_upper:   97.5th percentile of bootstrap distribution
      p_value:    fraction of bootstrap samples where delta <= 0
      significant: True if p_value < 0.05
    """
    rng = random.Random(seed)
    assert len(scores_a) == len(scores_b), "Score lists must be same length"
    n = len(scores_a)

    observed_delta = sum(scores_b) / n - sum(scores_a) / n

    bootstrap_deltas = []
    for _ in range(n_samples):
        indices = [rng.randint(0, n - 1) for _ in range(n)]
        boot_a = sum(scores_a[i] for i in indices) / n
        boot_b = sum(scores_b[i] for i in indices) / n
        bootstrap_deltas.append(boot_b - boot_a)

    bootstrap_deltas.sort()
    ci_lower = bootstrap_deltas[int(0.025 * n_samples)]
    ci_upper = bootstrap_deltas[int(0.975 * n_samples)]
    p_value = sum(1 for d in bootstrap_deltas if d <= 0) / n_samples

    return {
        "delta": round(observed_delta, 4),
        "ci_lower": round(ci_lower, 4),
        "ci_upper": round(ci_upper, 4),
        "p_value": round(p_value, 4),
        "significant": p_value < 0.05,
        "n_bootstrap": n_samples,
    }


def load_scores(path: Path) -> dict:
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    ablations_dir = PROJECT_ROOT / "ablations"

    baseline = load_scores(ablations_dir / "baseline_scores.json")
    trained  = load_scores(ablations_dir / "trained_scores.json")
    prompted = load_scores(ablations_dir / "prompted_scores.json")

    if not baseline:
        logger.error("baseline_scores.json not found. Run score_baseline.py first.")
        return

    results = {
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "seed": SEED,
        "n_tasks": baseline["total_tasks"],
        "baseline": {
            "scorer": baseline["scorer"],
            "pass_rate": baseline["pass_rate"],
            "avg_score": baseline["avg_score"],
        },
    }

    # ── Delta A: trained vs baseline ──────────────────────────────────
    if trained:
        baseline_scores = [r["total_score"] for r in baseline["task_results"]]
        trained_scores  = [r["total_score"] for r in trained["task_results"]]

        delta_a = paired_bootstrap(baseline_scores, trained_scores)
        delta_a["baseline_pass_rate"] = baseline["pass_rate"]
        delta_a["trained_pass_rate"]  = trained["pass_rate"]
        delta_a["baseline_avg_score"] = baseline["avg_score"]
        delta_a["trained_avg_score"]  = trained["avg_score"]
        delta_a["interpretation"] = (
            "POSITIVE — trained judge improves over baseline" if delta_a["delta"] > 0
            else "NEGATIVE — trained judge does not improve over baseline"
        )
        results["delta_a"] = delta_a

        print(f"\n{'='*60}")
        print(f"DELTA A — Trained Judge vs Baseline")
        print(f"{'='*60}")
        print(f"Baseline avg score: {baseline['avg_score']:.4f}  pass={baseline['pass_rate']:.1%}")
        print(f"Trained avg score:  {trained['avg_score']:.4f}  pass={trained['pass_rate']:.1%}")
        print(f"Delta:              {delta_a['delta']:+.4f}")
        print(f"95% CI:             [{delta_a['ci_lower']:+.4f}, {delta_a['ci_upper']:+.4f}]")
        print(f"p-value:            {delta_a['p_value']:.4f}")
        print(f"Significant:        {'YES ✅' if delta_a['significant'] else 'NO ❌'}")
        print(f"Interpretation:     {delta_a['interpretation']}")
    else:
        logger.warning("trained_scores.json not found — skipping Delta A")
        print("\nDelta A: SKIPPED (run score_trained.py in Colab first)")

    # ── Delta B: trained vs prompted ──────────────────────────────────
    if trained and prompted:
        trained_scores = [r["total_score"] for r in trained["task_results"]]

        # Handle case where prompted_scores only has summary stats (no task_results)
        if "task_results" in prompted:
            prompted_scores = [r["total_score"] for r in prompted["task_results"]]
            delta_b = paired_bootstrap(prompted_scores, trained_scores)
            delta_b["method"] = "paired_bootstrap"
        else:
            # Fall back to simple difference when per-task scores unavailable
            obs_delta = trained["avg_score"] - prompted["avg_score"]
            delta_b = {
                "delta": round(obs_delta, 4),
                "ci_lower": None,
                "ci_upper": None,
                "p_value": None,
                "significant": False,
                "method": "summary_only_no_bootstrap",
                "note": "Per-task scores not available — bootstrap skipped",
            }

        delta_b["prompted_pass_rate"] = prompted["pass_rate"]
        delta_b["trained_pass_rate"]  = trained["pass_rate"]
        delta_b["prompted_avg_score"] = prompted["avg_score"]
        delta_b["trained_avg_score"]  = trained["avg_score"]
        delta_b["interpretation"] = (
            "Training beats prompting — LoRA adds value beyond prompt engineering"
            if delta_b["delta"] > 0
            else "Prompting matches or beats training — honest finding, report in blog"
        )
        results["delta_b"] = delta_b

        print(f"\n{'='*60}")
        print(f"DELTA B — Trained Judge vs Prompted Base Model")
        print(f"{'='*60}")
        print(f"Prompted avg score: {prompted['avg_score']:.4f}  pass={prompted['pass_rate']:.1%}")
        print(f"Trained avg score:  {trained['avg_score']:.4f}  pass={trained['pass_rate']:.1%}")
        print(f"Delta:              {delta_b['delta']:+.4f}")
        if delta_b.get('ci_lower') is not None:
            print(f"95% CI:             [{delta_b['ci_lower']:+.4f}, {delta_b['ci_upper']:+.4f}]")
            print(f"p-value:            {delta_b['p_value']:.4f}")
            print(f"Significant:        {'YES ✅' if delta_b['significant'] else 'NO ❌'}")
        else:
            print(f"Bootstrap:          SKIPPED (per-task scores not available)")
        print(f"Interpretation:     {delta_b['interpretation']}")
    else:
        logger.warning("trained_scores.json or prompted_scores.json not found — skipping Delta B")
        print("\nDelta B: SKIPPED (run score_trained.py and score_prompted.py in Colab first)")

    # ── Delta C: informational ─────────────────────────────────────────
    # Reuse Week 10 τ²-Bench score if available — no new runs
    tau2_score = None  # set this if you have a Week 10 τ²-Bench score
    if tau2_score and trained:
        results["delta_c"] = {
            "tau2_bench_score": tau2_score,
            "tenacious_bench_score": trained["avg_score"] if trained else None,
            "interpretation": "Informational only — tests domain specificity, not used for deployment decision",
        }
        print(f"\n{'='*60}")
        print(f"DELTA C — Domain Specificity (Informational)")
        print(f"{'='*60}")
        print(f"τ²-Bench score (Week 10):     {tau2_score:.4f}")
        print(f"Tenacious-Bench score:         {trained['avg_score']:.4f}")
        print(f"Note: No new τ²-Bench runs — reusing Week 10 number")
    else:
        results["delta_c"] = {
            "note": "No Week 10 τ²-Bench score available — Delta C skipped",
            "interpretation": "Informational only — not required for deployment decision",
        }
        print(f"\nDelta C: SKIPPED (no Week 10 τ²-Bench score on file)")

    # ── Save results ───────────────────────────────────────────────────
    out_path = ablations_dir / "ablation_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nAblation results saved to {out_path}")

    # ── Deployment recommendation ──────────────────────────────────────
    if trained:
        delta_a = results.get("delta_a", {})
        delta_b = results.get("delta_b", {})

        print(f"\n{'='*60}")
        print(f"DEPLOYMENT RECOMMENDATION")
        print(f"{'='*60}")

        if delta_a.get("delta", 0) > 0 and delta_a.get("significant"):
            if delta_b.get("delta", 0) > 0:
                print("DEPLOY — trained judge improves over baseline AND beats prompting")
            else:
                print("DEPLOY WITH CAVEAT — trained judge improves over baseline")
                print("  but prompting matches training (Delta B negative)")
                print("  Consider: prompt engineering may be sufficient for production")
        elif delta_a.get("delta", 0) > 0 and not delta_a.get("significant"):
            print("DO NOT DEPLOY YET — improvement not statistically significant")
            print("  Recommendation: collect more training data or increase epochs")
        else:
            print("DO NOT DEPLOY — trained judge does not improve over baseline")
            print("  Recommendation: review training data quality and pair construction")


if __name__ == "__main__":
    main()
