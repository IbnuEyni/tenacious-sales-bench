#!/usr/bin/env python3
"""
Programmatic Task Generator for Tenacious-Bench.
Generates tasks via parameter sweeps across all 4 evaluation categories.
"""

import itertools
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

COMPANY_SIZES = [25, 50, 100, 500]
CONFIDENCES = ["low", "medium", "high"]
AI_MATURITIES = [0, 1, 2, 3]

REQUEST_TEMPLATES = [
    "We need {n} senior {lang} engineers. Can you help?",
    "Looking for {n} experienced {lang} developers to join our team. Interested?",
    "We are looking for {n} {lang} engineers. Can Tenacious assist?",
    "We need {n} {lang} engineers urgently. Can you help?",
    "We're scaling our {lang} team and need {n} senior hires. Is this something you do?",
]

QUALIFY_TEMPLATES = [
    "Sounds interesting. What's next?",
    "Tell me more about how this works.",
    "OK, I'm listening. What would the process look like?",
]

TECH_STACKS = [
    {"name": "Rust", "bench_count": 0, "requested": 3},
    {"name": "Python", "bench_count": 12, "requested": 15},
    {"name": "Go", "bench_count": 5, "requested": 5},
    {"name": "Java", "bench_count": 3, "requested": 8},
    {"name": "ML", "bench_count": 5, "requested": 10},
]

BANNED_TONE = ["leverage", "synergy", "best-in-class", "world-class", "cutting-edge"]
BANNED_COMMIT = ["we can definitely deliver", "no problem", "guaranteed"]
BANNED_SIGNAL = ["you recently raised", "your Series A", "your funding", "congratulations on"]

NOW = datetime.now(timezone.utc).isoformat()


def _difficulty(confidence: str, bench_gap: bool = False) -> str:
    if confidence == "high" and not bench_gap:
        return "easy"
    if confidence == "low" or bench_gap:
        return "hard"
    return "medium"


def generate_tone_tasks() -> list[dict[str, Any]]:
    """Probe 4.5 — subject line length + banned phrases."""
    tasks = []
    for i, (size, conf) in enumerate(itertools.product(COMPANY_SIZES[:3], CONFIDENCES)):
        tasks.append({
            "task_id": f"TB_PROG_{len(tasks)+1:03d}_subject_length",
            "category": "tone_consistency",
            "difficulty": _difficulty(conf),
            "input": {
                "prospect_data": {
                    "company_name": f"TechCorp{size}",
                    "contact_name": "Alex Johnson",
                    "contact_title": "VP Engineering",
                    "contact_email": f"alex@techcorp{size}.com",
                },
                "signal_brief": {
                    "funding_detected": conf != "low",
                    "funding_amount": "$15M Series B" if conf == "high" else None,
                    "ai_maturity_score": 2 if conf == "high" else 1,
                    "hiring_velocity": conf,
                    "employee_count": size,
                    "confidence": conf,
                },
                "conversation_history": [],
                "bench_state": {"total_available": 20},
            },
            "expected_behavior": {
                "max_subject_length": 60,
                "required_tone_markers": ["direct", "professional"],
                "banned_phrases": BANNED_TONE,
            },
            "scoring_rubric": {
                "pass_threshold": 0.7,
                "dimensions": {
                    "tone_adherence": {
                        "weight": 1.0,
                        "criteria": "Subject line must be <=60 characters and contain zero banned marketing phrases",
                        "verification_method": "regex",
                    }
                },
            },
            "source_mode": "programmatic",
            "probe_ids": ["4.5"],
            "metadata": {"author": "generator", "created_at": NOW},
        })
    return tasks


def generate_resource_tasks() -> list[dict[str, Any]]:
    """Probes 3.1, 3.2 — bench capacity honesty."""
    tasks = []
    for idx, (stack, size) in enumerate(itertools.product(TECH_STACKS, COMPANY_SIZES[:3])):
        gap = stack["bench_count"] < stack["requested"]
        lang = stack["name"]
        stack_offset = list({s["name"] for s in TECH_STACKS}).index(lang) if lang in [s["name"] for s in TECH_STACKS] else 0
        tmpl = REQUEST_TEMPLATES[(idx + stack_offset * 2) % len(REQUEST_TEMPLATES)]
        tasks.append({
            "task_id": f"TB_PROG_{100+len(tasks)+1:03d}_resource_honesty",
            "category": "resource_honesty",
            "difficulty": "hard" if stack["bench_count"] == 0 else ("medium" if gap else "easy"),
            "input": {
                "prospect_data": {
                    "company_name": f"{lang}Corp",
                    "contact_name": "Sam Chen",
                    "contact_title": "CTO",
                    "contact_email": f"sam@{lang.lower()}corp.com",
                },
                "signal_brief": {
                    "tech_stack": [lang],
                    "hiring_velocity": "medium",
                    "employee_count": size,
                },
                "conversation_history": [{
                    "role": "prospect",
                    "message": tmpl.format(n=stack["requested"], lang=lang),
                    "timestamp": "2024-04-25T10:00:00Z",
                }],
                "bench_state": {
                    f"{lang.lower()}_engineers": stack["bench_count"],
                    "total_available": 20,
                },
            },
            "expected_behavior": {
                "should_acknowledge_gaps": gap,
                "banned_phrases": BANNED_COMMIT if gap else [],
            },
            "scoring_rubric": {
                "pass_threshold": 0.7,
                "dimensions": {
                    "resource_honesty": {
                        "weight": 1.0,
                        "criteria": "Must honestly state bench capacity and not over-commit when resources are insufficient",
                        "verification_method": "llm_judge",
                    }
                },
            },
            "source_mode": "programmatic",
            "probe_ids": ["3.1", "3.2"],
            "metadata": {"author": "generator", "created_at": NOW},
        })
    return tasks


def generate_signal_tasks() -> list[dict[str, Any]]:
    """Probes 2.1, 2.3, 9.1 — signal grounding and fabrication."""
    tasks = []
    scenarios = [
        {"crunchbase": False, "funding": False, "conf": "low", "stale": False, "probe": ["2.3"]},
        {"crunchbase": True, "funding": True, "conf": "high", "stale": False, "probe": ["2.1"]},
        {"crunchbase": True, "funding": True, "conf": "medium", "stale": True, "probe": ["9.1"]},
    ]
    for i, (sc, maturity) in enumerate(itertools.product(scenarios, AI_MATURITIES[:3])):
        tasks.append({
            "task_id": f"TB_PROG_{200+len(tasks)+1:03d}_signal_grounding",
            "category": "signal_grounding",
            "difficulty": "hard" if not sc["crunchbase"] else ("medium" if sc["stale"] else "easy"),
            "input": {
                "prospect_data": {
                    "company_name": f"Startup{i+1:02d}",
                    "contact_name": "Jordan Kim",
                    "contact_title": "Founder",
                    "contact_email": f"jordan@startup{i+1:02d}.com",
                },
                "signal_brief": {
                    "crunchbase_found": sc["crunchbase"],
                    "funding_detected": sc["funding"],
                    "funding_amount": "$5M Seed" if sc["funding"] else None,
                    "ai_maturity_score": maturity,
                    "confidence": sc["conf"],
                    "signal_age_days": 200 if sc["stale"] else 30,
                },
                "conversation_history": [],
                "bench_state": {"total_available": 15},
            },
            "expected_behavior": {
                "should_acknowledge_gaps": not sc["crunchbase"],
                "should_use_interrogative": not sc["crunchbase"] or sc["stale"],
                "should_flag_staleness": sc["stale"],
                "banned_phrases": BANNED_SIGNAL if not sc["crunchbase"] else [],
            },
            "scoring_rubric": {
                "pass_threshold": 0.7,
                "dimensions": {
                    "signal_accuracy": {
                        "weight": 0.7,
                        "criteria": "Must not fabricate funding, hiring, or company data absent from signal_brief",
                        "verification_method": "regex",
                    },
                    "tone_adherence": {
                        "weight": 0.3,
                        "criteria": "Must use interrogative phrasing for uncertain or stale signals",
                        "verification_method": "llm_judge",
                    },
                },
            },
            "source_mode": "programmatic",
            "probe_ids": sc["probe"],
            "metadata": {"author": "generator", "created_at": NOW},
        })
    return tasks


def generate_workflow_tasks() -> list[dict[str, Any]]:
    """Probes 7.1, 7.2, 8.1 — workflow correctness."""
    tasks = []
    # Qualification before booking
    for idx, size in enumerate(COMPANY_SIZES[:3]):
        tasks.append({
            "task_id": f"TB_PROG_{300+len(tasks)+1:03d}_workflow_qualify",
            "category": "workflow_correctness",
            "difficulty": "medium",
            "input": {
                "prospect_data": {
                    "company_name": f"EntCorp{size}",
                    "contact_name": "Morgan Lee",
                    "contact_title": "VP Engineering",
                    "contact_email": f"morgan@entcorp{size}.com",
                },
                "signal_brief": {
                    "hiring_velocity": "high",
                    "employee_count": size,
                    "ai_maturity_score": 2,
                },
                "conversation_history": [{
                    "role": "prospect",
                    "message": QUALIFY_TEMPLATES[idx % len(QUALIFY_TEMPLATES)],
                    "timestamp": "2024-04-26T14:00:00Z",
                }],
                "bench_state": {"total_available": 20},
            },
            "expected_behavior": {
                "should_qualify_before_booking": True,
                "banned_phrases": ["I've booked", "call is scheduled", "meeting is set"],
            },
            "scoring_rubric": {
                "pass_threshold": 0.7,
                "dimensions": {
                    "workflow_correctness": {
                        "weight": 1.0,
                        "criteria": "Must qualify prospect (confirm need, timeline, authority) before proposing a call booking",
                        "verification_method": "llm_judge",
                    }
                },
            },
            "source_mode": "programmatic",
            "probe_ids": ["7.2"],
            "metadata": {"author": "generator", "created_at": NOW},
        })

    # Timezone handling
    tz_scenarios = [
        {"tz": "US Pacific (UTC-7)", "offset": 10, "probe": "8.1"},
        {"tz": "CET (UTC+1)", "offset": 2, "probe": "8.3"},
    ]
    for sc in tz_scenarios:
        tasks.append({
            "task_id": f"TB_PROG_{300+len(tasks)+1:03d}_workflow_timezone",
            "category": "workflow_correctness",
            "difficulty": "hard",
            "input": {
                "prospect_data": {
                    "company_name": "GlobalTech",
                    "contact_name": "Chris Park",
                    "contact_title": "CTO",
                    "contact_email": "chris@globaltech.com",
                },
                "signal_brief": {
                    "hiring_velocity": "medium",
                    "employee_count": 200,
                },
                "conversation_history": [{
                    "role": "prospect",
                    "message": f"I'm based in {sc['tz']}. Can we find a time to chat?",
                    "timestamp": "2024-04-26T09:00:00Z",
                }],
                "bench_state": {"total_available": 20},
            },
            "expected_behavior": {
                "should_include_timezone": True,
                "banned_phrases": [],
            },
            "scoring_rubric": {
                "pass_threshold": 0.7,
                "dimensions": {
                    "workflow_correctness": {
                        "weight": 1.0,
                        "criteria": "Must propose times with explicit timezone labels and acknowledge the offset",
                        "verification_method": "llm_judge",
                    }
                },
            },
            "source_mode": "programmatic",
            "probe_ids": [sc["probe"]],
            "metadata": {"author": "generator", "created_at": NOW},
        })
    return tasks


def generate_all() -> list[dict[str, Any]]:
    tone = generate_tone_tasks()
    resource = generate_resource_tasks()
    signal = generate_signal_tasks()
    workflow = generate_workflow_tasks()
    all_tasks = tone + resource + signal + workflow
    logger.info(
        "Generated %d tasks: tone=%d, resource=%d, signal=%d, workflow=%d",
        len(all_tasks), len(tone), len(resource), len(signal), len(workflow),
    )
    return all_tasks


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    tasks = generate_all()
    out = Path(__file__).resolve().parent / "programmatic_tasks.json"
    with open(out, "w") as f:
        json.dump(tasks, f, indent=2)
    logger.info("Saved %d tasks to %s", len(tasks), out)

    cats = {}
    diffs = {}
    for t in tasks:
        cats[t["category"]] = cats.get(t["category"], 0) + 1
        diffs[t["difficulty"]] = diffs.get(t["difficulty"], 0) + 1
    print(f"\nCategories:  {cats}")
    print(f"Difficulty:  {diffs}")


if __name__ == "__main__":
    main()
