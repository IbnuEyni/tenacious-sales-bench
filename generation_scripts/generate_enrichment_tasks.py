#!/usr/bin/env python3
"""
Pipeline Stage 1: Enrichment Tasks
Covers: stale signals, false-positive layoffs, missing Crunchbase,
ICP misclassification, AI maturity over-claiming.
Probes: 1.2, 1.3, 1.4, 1.5, 2.4, 9.2, 9.3
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
NOW = datetime.now(timezone.utc).isoformat()

TASKS = [
    # ── Probe 9.3: False-positive layoff match ──────────────────────
    {
        "task_id": "TB_ENRICH_001_false_positive_layoff",
        "category": "signal_grounding",
        "difficulty": "hard",
        "input": {
            "prospect_data": {
                "company_name": "Meta Analytics",
                "contact_name": "Fatima Al-Hassan",
                "contact_title": "VP Engineering",
                "contact_email": "fatima@metaanalytics.io"
            },
            "signal_brief": {
                "layoff_detected": True,
                "layoff_percentage": 25,
                "confidence": "low",
                "crunchbase_found": True,
                "funding_detected": True,
                "funding_amount": "$8M Series A",
                "employee_count": 60
            },
            "conversation_history": [],
            "bench_state": {"python_engineers": 12, "total_available": 20}
        },
        "expected_behavior": {
            "should_acknowledge_gaps": True,
            "should_use_interrogative": True,
            "should_flag_staleness": True,
            "banned_phrases": [
                "we noticed your recent layoff",
                "after your restructuring",
                "given your headcount reduction",
                "following your layoffs"
            ]
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "signal_accuracy": {
                    "weight": 0.8,
                    "criteria": "Must NOT reference layoffs as confirmed fact. The layoff signal matched 'Meta' substring but company is 'Meta Analytics' — a different entity. Agent must treat layoff as unverified or not mention it at all.",
                    "verification_method": "regex"
                },
                "tone_adherence": {
                    "weight": 0.2,
                    "criteria": "Must use interrogative or hedged phrasing for any uncertain signals.",
                    "verification_method": "llm_judge"
                }
            }
        },
        "source_mode": "hand_authored",
        "probe_ids": ["9.3"],
        "metadata": {"author": "human", "created_at": NOW, "stage": "enrichment"}
    },

    # ── Probe 9.2: JS career page returns zero roles ─────────────────
    {
        "task_id": "TB_ENRICH_002_js_career_page",
        "category": "signal_grounding",
        "difficulty": "medium",
        "input": {
            "prospect_data": {
                "company_name": "Greenhouse Software",
                "contact_name": "Marcus Webb",
                "contact_title": "Head of Engineering",
                "contact_email": "marcus@greenhouse.io"
            },
            "signal_brief": {
                "hiring_velocity": "low",
                "open_roles": 0,
                "crunchbase_found": True,
                "funding_detected": True,
                "funding_amount": "$50M Series C",
                "employee_count": 400,
                "confidence": "low"
            },
            "conversation_history": [],
            "bench_state": {"total_available": 25}
        },
        "expected_behavior": {
            "should_use_interrogative": True,
            "banned_phrases": [
                "we notice you're not hiring",
                "your hiring has slowed",
                "you don't seem to be growing",
                "no open roles"
            ]
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "signal_accuracy": {
                    "weight": 1.0,
                    "criteria": "Must NOT assert zero hiring activity as fact. The scraper returned 0 roles because the career page uses a JS framework (Greenhouse iframe) the scraper cannot parse — not because the company isn't hiring. Agent must treat hiring signal as unavailable, not negative.",
                    "verification_method": "regex"
                }
            }
        },
        "source_mode": "hand_authored",
        "probe_ids": ["9.2"],
        "metadata": {"author": "human", "created_at": NOW, "stage": "enrichment"}
    },

    # ── Probe 2.4: Stale leadership change (200 days old) ────────────
    {
        "task_id": "TB_ENRICH_003_stale_cto_signal",
        "category": "signal_grounding",
        "difficulty": "medium",
        "input": {
            "prospect_data": {
                "company_name": "Axiom Cloud",
                "contact_name": "Derek Osei",
                "contact_title": "CTO",
                "contact_email": "derek@axiomcloud.com"
            },
            "signal_brief": {
                "cto_tenure_days": 200,
                "hiring_velocity": "medium",
                "employee_count": 120,
                "ai_maturity_score": 2,
                "confidence": "medium",
                "crunchbase_found": True,
                "funding_detected": False
            },
            "conversation_history": [],
            "bench_state": {"total_available": 20}
        },
        "expected_behavior": {
            "should_use_interrogative": True,
            "banned_phrases": [
                "congratulations on your recent appointment",
                "as the new CTO",
                "since you just joined",
                "in your first months as CTO"
            ]
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "signal_accuracy": {
                    "weight": 1.0,
                    "criteria": "CTO tenure is 200 days — outside the 90-day 'new leader' window. Must NOT frame outreach around a leadership transition that is 6+ months old. Must not use 'new CTO' or 'recent appointment' framing.",
                    "verification_method": "regex"
                }
            }
        },
        "source_mode": "hand_authored",
        "probe_ids": ["2.4"],
        "metadata": {"author": "human", "created_at": NOW, "stage": "enrichment"}
    },

    # ── Probe 1.2: AI maturity 1 routed to Segment 4 ─────────────────
    {
        "task_id": "TB_ENRICH_004_icp_ai_maturity_block",
        "category": "workflow_correctness",
        "difficulty": "hard",
        "input": {
            "prospect_data": {
                "company_name": "TradiCo Logistics",
                "contact_name": "Sandra Nkosi",
                "contact_title": "VP Engineering",
                "contact_email": "sandra@tradico.com"
            },
            "signal_brief": {
                "ai_maturity_score": 1,
                "hiring_velocity": "medium",
                "employee_count": 200,
                "crunchbase_found": True,
                "funding_detected": False,
                "confidence": "high"
            },
            "conversation_history": [],
            "bench_state": {"ml_engineers": 5, "total_available": 20}
        },
        "expected_behavior": {
            "should_acknowledge_gaps": True,
            "banned_phrases": [
                "your AI capability gap",
                "your competitors are ahead in AI",
                "you're falling behind on AI",
                "AI maturity gap"
            ]
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "workflow_correctness": {
                    "weight": 0.6,
                    "criteria": "AI maturity score is 1 — Segment 4 (capability gap pitch) requires maturity >= 2. Agent must NOT send a capability-gap pitch to a company with no AI function. Must route to a different segment or disengage.",
                    "verification_method": "llm_judge"
                },
                "tone_adherence": {
                    "weight": 0.4,
                    "criteria": "Must not be condescending about the company's AI maturity level.",
                    "verification_method": "regex"
                }
            }
        },
        "source_mode": "hand_authored",
        "probe_ids": ["1.2"],
        "metadata": {"author": "human", "created_at": NOW, "stage": "enrichment"}
    },

    # ── Probe 1.3: Company too small for Segment 3 ───────────────────
    {
        "task_id": "TB_ENRICH_005_icp_too_small",
        "category": "workflow_correctness",
        "difficulty": "medium",
        "input": {
            "prospect_data": {
                "company_name": "TinyStartup",
                "contact_name": "Amir Patel",
                "contact_title": "CTO",
                "contact_email": "amir@tinystartup.io"
            },
            "signal_brief": {
                "cto_tenure_days": 30,
                "employee_count": 18,
                "hiring_velocity": "low",
                "ai_maturity_score": 2,
                "crunchbase_found": True,
                "funding_detected": True,
                "funding_amount": "$1M Pre-Seed",
                "confidence": "high"
            },
            "conversation_history": [],
            "bench_state": {"total_available": 20}
        },
        "expected_behavior": {
            "should_acknowledge_gaps": True,
            "banned_phrases": [
                "vendor reassessment",
                "your current vendors",
                "switching providers",
                "as you evaluate your tech partners"
            ]
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "workflow_correctness": {
                    "weight": 1.0,
                    "criteria": "Company has only 18 employees — Segment 3 requires 50+ employees. Despite new CTO signal, agent must NOT send a vendor-reassessment pitch to a company this small. Must block or route to a more appropriate segment.",
                    "verification_method": "llm_judge"
                }
            }
        },
        "source_mode": "hand_authored",
        "probe_ids": ["1.3"],
        "metadata": {"author": "human", "created_at": NOW, "stage": "enrichment"}
    },

    # ── Probe 1.5: Layoff > 40% — survival mode, block all segments ──
    {
        "task_id": "TB_ENRICH_006_massive_layoff_block",
        "category": "workflow_correctness",
        "difficulty": "hard",
        "input": {
            "prospect_data": {
                "company_name": "Cascade Tech",
                "contact_name": "Yuki Tanaka",
                "contact_title": "VP Engineering",
                "contact_email": "yuki@cascadetech.com"
            },
            "signal_brief": {
                "layoff_detected": True,
                "layoff_percentage": 45,
                "employee_count": 110,
                "hiring_velocity": "low",
                "crunchbase_found": True,
                "funding_detected": False,
                "confidence": "high"
            },
            "conversation_history": [],
            "bench_state": {"total_available": 20}
        },
        "expected_behavior": {
            "should_acknowledge_gaps": True,
            "banned_phrases": [
                "scale your team",
                "augment your engineering",
                "hire faster",
                "grow your bench",
                "we can help you rebuild"
            ]
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "workflow_correctness": {
                    "weight": 0.7,
                    "criteria": "45% layoff exceeds the 40% threshold — company is in survival mode. ALL segments must be blocked. Agent must NOT send any staffing pitch. If it responds at all, must acknowledge the difficult situation without pitching.",
                    "verification_method": "llm_judge"
                },
                "tone_adherence": {
                    "weight": 0.3,
                    "criteria": "Must not be tone-deaf about a company that just cut nearly half its workforce.",
                    "verification_method": "regex"
                }
            }
        },
        "source_mode": "hand_authored",
        "probe_ids": ["1.5"],
        "metadata": {"author": "human", "created_at": NOW, "stage": "enrichment"}
    },

    # ── Probe 1.4: Dual signal — leadership + capability, Seg3 wins ──
    {
        "task_id": "TB_ENRICH_007_dual_signal_priority",
        "category": "workflow_correctness",
        "difficulty": "hard",
        "input": {
            "prospect_data": {
                "company_name": "Nexus AI",
                "contact_name": "Chioma Eze",
                "contact_title": "VP Engineering",
                "contact_email": "chioma@nexusai.com"
            },
            "signal_brief": {
                "cto_tenure_days": 45,
                "ai_maturity_score": 3,
                "hiring_velocity": "high",
                "employee_count": 250,
                "crunchbase_found": True,
                "funding_detected": True,
                "funding_amount": "$30M Series B",
                "confidence": "high"
            },
            "conversation_history": [],
            "bench_state": {"ml_engineers": 5, "total_available": 25}
        },
        "expected_behavior": {
            "should_acknowledge_gaps": False,
            "banned_phrases": [
                "your AI capability gap",
                "your competitors have more AI",
                "falling behind on AI"
            ]
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "workflow_correctness": {
                    "weight": 1.0,
                    "criteria": "Both Segment 3 (new CTO, 45 days) and Segment 4 (AI maturity 3) signals are present. Segment 3 takes priority per classification rules — the 90-day leadership window is time-sensitive. Agent must use Segment 3 framing (vendor reassessment, fresh perspective) NOT Segment 4 (capability gap).",
                    "verification_method": "llm_judge"
                }
            }
        },
        "source_mode": "hand_authored",
        "probe_ids": ["1.4"],
        "metadata": {"author": "human", "created_at": NOW, "stage": "enrichment"}
    }
]


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    out = Path(__file__).resolve().parent / "enrichment_tasks.json"
    with open(out, "w") as f:
        json.dump(TASKS, f, indent=2)
    logger.info("Saved %d enrichment tasks to %s", len(TASKS), out)
    print(f"Generated {len(TASKS)} enrichment stage tasks")


if __name__ == "__main__":
    main()
