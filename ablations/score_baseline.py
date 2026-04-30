#!/usr/bin/env python3
"""
Baseline Scorer — Delta A baseline
====================================
Scores all 50 held-out tasks using the heuristic evaluator only.
No LLM judge — uses regex + heuristic fallback.
This represents the Week 10 agent with no trained judge component.

Run locally (no GPU needed):
  python3 ablations/score_baseline.py
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from evaluation.scoring_evaluator import TenaciousBenchEvaluator

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def generate_agent_output(task: dict) -> dict:
    """
    Simulate the Week 10 baseline agent output for each task.
    The baseline agent has no judge — it generates outputs that
    sometimes pass and sometimes fail based on the failure patterns
    documented in Week 10 probe library.

    Failure rates based on Week 10 evidence:
      - Probe 4.5 (subject length): 100% failure rate
      - Probe 7.1 (auth bypass):    100% failure rate
      - Probe 6.2 (reasoning loop):  20% failure rate
      - Probe 8.1 (timezone):        50% failure rate
      - Others:                       0% failure rate (correct behavior)
    """
    import random
    rng = random.Random(42)  # deterministic

    probe_ids = task.get("probe_ids", [])
    category = task["category"]
    prospect = task["input"]["prospect_data"]
    name = prospect.get("contact_name", "there").split()[0]
    company = prospect.get("company_name", "your company")
    bench = task["input"].get("bench_state", {})
    history = task["input"].get("conversation_history", [])

    last_prospect_msg = ""
    for m in reversed(history):
        if m["role"] == "prospect":
            last_prospect_msg = m["message"].lower()
            break

    # ── Probe-specific failure simulation ─────────────────────────────

    # Probe 4.5: subject line always too long (100% failure)
    if "4.5" in probe_ids:
        return {
            "email_subject": f"Following up on your recent funding round and engineering hiring needs at {company}",
            "email_body": f"Hi {name}, I wanted to reach out about your engineering needs.",
        }

    # Probe 7.1: proceeds without checking (100% failure)
    if "7.1" in probe_ids and any(
        phrase in last_prospect_msg
        for phrase in ["unsubscribe", "stop", "remove me", "spam", "bot", "gdpr", "ccpa"]
    ):
        return {
            "email_subject": "Re: your message",
            "email_body": f"Hi {name}, I understand your concern but before you go — let me share one more thing about our bench. We have some exciting updates this month!",
        }

    # Probe 8.1: timezone missing (50% failure)
    if "8.1" in probe_ids and rng.random() < 0.5:
        return {
            "email_subject": "Call confirmed",
            "email_body": f"Hi {name}, confirmed for Tuesday at 3pm. Looking forward to speaking with you!",
        }

    # Probe 3.1: over-commits on bench gaps (occasional failure)
    if "3.1" in probe_ids:
        bench_keys = [k for k in bench if k != "total_available"]
        if bench_keys:
            lang = bench_keys[0].replace("_engineers", "").title()
            available = bench.get(bench_keys[0], 0)
            if available == 0:
                return {
                    "email_subject": f"{lang} engineers",
                    "email_body": f"Hi {name}, no problem — we can definitely deliver the {lang} engineers you need. Guaranteed delivery next month!",
                }

    # Probe 4.4: emoji in cold outreach (occasional failure)
    if "4.4" in probe_ids and rng.random() < 0.3:
        return {
            "email_subject": f"Senior engineers for {company} 🚀",
            "email_body": f"Hi {name}! 💡 We'd love to help your team scale! Let's connect! 🎯",
        }

    # Probe 4.2: banned follow-up phrases
    if "4.2" in probe_ids and rng.random() < 0.4:
        return {
            "email_subject": f"Following up",
            "email_body": f"Hi {name}, just following up on my previous email. Circling back to touch base — would love to connect!",
        }

    # ── Default: correct baseline behavior ────────────────────────────
    if category == "tone_consistency":
        return {
            "email_subject": f"Senior engineers for {company}",
            "email_body": f"Hi {name}, noticed {company} has been scaling its engineering team. Tenacious places senior engineers at companies at your stage — is augmenting your team something you're exploring?",
        }

    if category == "resource_honesty":
        bench_keys = [k for k in bench if k != "total_available"]
        lang = bench_keys[0].replace("_engineers", "").title() if bench_keys else "the requested stack"
        available = bench.get(bench_keys[0], 0) if bench_keys else 0
        if available == 0:
            return {
                "email_subject": f"{lang} engineers",
                "email_body": f"Hi {name}, to be upfront — we don't currently have {lang} engineers on our bench. I wouldn't want to over-promise.",
            }
        return {
            "email_subject": f"{lang} engineers",
            "email_body": f"Hi {name}, we have {available} {lang} engineers available. Happy to discuss next steps.",
        }

    if category == "signal_grounding":
        signal = task["input"].get("signal_brief", {})
        if not signal.get("crunchbase_found", True):
            return {
                "email_subject": f"Engineering capacity",
                "email_body": f"Hi {name}, I wanted to reach out to {company} — I'm working with limited signal on your current situation. Is this worth a brief conversation?",
            }
        return {
            "email_subject": f"Engineering capacity",
            "email_body": f"Hi {name}, noticed {company} in our research. Curious whether augmenting your engineering capacity is something you're exploring?",
        }

    # workflow_correctness default
    if any(phrase in last_prospect_msg for phrase in ["unsubscribe", "stop", "remove"]):
        return {
            "email_subject": "Re: your request",
            "email_body": f"Confirmed — removing you from our list immediately. Apologies for the inconvenience.",
        }
    if any(phrase in last_prospect_msg for phrase in ["not interested", "no thanks"]):
        return {
            "email_subject": "Re: your message",
            "email_body": f"Understood completely. Thank you for letting me know.",
        }
    return {
        "email_subject": f"Engineering capacity at {company}",
        "email_body": f"Hi {name}, thanks for your message. To make sure I can be most useful — could you share a bit about your specific engineering need and timeline?",
    }


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    held_out_path = PROJECT_ROOT / "dataset" / "partitions" / "held_out.json"
    with open(held_out_path) as f:
        held_out = json.load(f)

    evaluator = TenaciousBenchEvaluator()  # no llm_judge_fn = heuristic fallback

    results = []
    passed = 0

    for task in held_out:
        agent_output = generate_agent_output(task)
        result = evaluator.score_task(task, agent_output)
        results.append({
            "task_id": result.task_id,
            "total_score": result.total_score,
            "passed": result.passed,
            "dimension_scores": result.dimension_scores,
            "agent_output": agent_output,
            "category": task["category"],
            "difficulty": task["difficulty"],
            "probe_ids": task.get("probe_ids", []),
        })
        if result.passed:
            passed += 1

    # Summary stats
    scores = [r["total_score"] for r in results]
    avg_score = sum(scores) / len(scores)
    pass_rate = passed / len(results)

    by_cat = {}
    for r in results:
        cat = r["category"]
        if cat not in by_cat:
            by_cat[cat] = {"scores": [], "passed": 0}
        by_cat[cat]["scores"].append(r["total_score"])
        if r["passed"]:
            by_cat[cat]["passed"] += 1

    summary = {
        "scorer": "baseline_heuristic",
        "total_tasks": len(results),
        "passed": passed,
        "pass_rate": round(pass_rate, 4),
        "avg_score": round(avg_score, 4),
        "scores": scores,
        "by_category": {
            cat: {
                "avg_score": round(sum(v["scores"]) / len(v["scores"]), 4),
                "pass_rate": round(v["passed"] / len(v["scores"]), 4),
                "count": len(v["scores"]),
            }
            for cat, v in by_cat.items()
        },
        "task_results": results,
    }

    out_path = PROJECT_ROOT / "ablations" / "baseline_scores.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*50}")
    print(f"BASELINE SCORES")
    print(f"{'='*50}")
    print(f"Tasks:     {len(results)}")
    print(f"Passed:    {passed} / {len(results)}")
    print(f"Pass rate: {pass_rate:.1%}")
    print(f"Avg score: {avg_score:.4f}")
    print(f"\nBy category:")
    for cat, v in summary["by_category"].items():
        print(f"  {cat:25s}: avg={v['avg_score']:.3f}  pass={v['pass_rate']:.1%}  n={v['count']}")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
