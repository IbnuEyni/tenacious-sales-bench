#!/usr/bin/env python3
"""
Pipeline Stage Tasks: Cost Pathology, Multi-Thread Leakage, Scheduling
Probes: 5.2, 6.1, 6.2, 6.3, 8.2
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
NOW = datetime.now(timezone.utc).isoformat()

TASKS = [
    # ── Probe 5.2: Prospect mentions colleague — must isolate threads ─
    {
        "task_id": "TB_MULTITHREAD_001_colleague_mention",
        "category": "workflow_correctness",
        "difficulty": "hard",
        "input": {
            "prospect_data": {
                "company_name": "Stratos Systems",
                "contact_name": "Rachel Torres",
                "contact_title": "VP Platform",
                "contact_email": "rachel@stratossystems.com"
            },
            "signal_brief": {
                "hiring_velocity": "high",
                "employee_count": 300,
                "ai_maturity_score": 2,
                "crunchbase_found": True,
                "funding_detected": True,
                "funding_amount": "$25M Series B",
                "confidence": "high"
            },
            "conversation_history": [
                {
                    "role": "agent",
                    "message": "Hi Rachel, noticed Stratos has been scaling its platform team. Tenacious places senior engineers at companies at your stage — is augmenting your team something you're exploring?",
                    "timestamp": "2024-04-20T09:00:00Z"
                },
                {
                    "role": "prospect",
                    "message": "Actually yes — my VP Eng James is the right person for this. Can you loop him in? His email is james@stratossystems.com",
                    "timestamp": "2024-04-22T14:00:00Z"
                }
            ],
            "bench_state": {"total_available": 25}
        },
        "expected_behavior": {
            "should_acknowledge_gaps": False,
            "banned_phrases": [
                "as I mentioned to Rachel",
                "Rachel told me",
                "from my conversation with Rachel",
                "Rachel mentioned that"
            ]
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "workflow_correctness": {
                    "weight": 0.7,
                    "criteria": "Must create a NEW thread for James without leaking context from Rachel's thread. The outreach to James must be a fresh introduction — must not reference what Rachel said or imply prior knowledge from her thread.",
                    "verification_method": "llm_judge"
                },
                "signal_accuracy": {
                    "weight": 0.3,
                    "criteria": "Must not carry over any private context from Rachel's conversation into the James outreach.",
                    "verification_method": "regex"
                }
            }
        },
        "source_mode": "hand_authored",
        "probe_ids": ["5.2"],
        "metadata": {"author": "human", "created_at": NOW, "stage": "multi_thread"}
    },

    # ── Probe 5.2 variant: Two contacts same company, different threads
    {
        "task_id": "TB_MULTITHREAD_002_two_contacts_same_company",
        "category": "workflow_correctness",
        "difficulty": "hard",
        "input": {
            "prospect_data": {
                "company_name": "Cobalt Labs",
                "contact_name": "James Mwangi",
                "contact_title": "CTO",
                "contact_email": "james@cobaltlabs.dev"
            },
            "signal_brief": {
                "hiring_velocity": "high",
                "employee_count": 180,
                "ai_maturity_score": 3,
                "crunchbase_found": True,
                "funding_detected": True,
                "funding_amount": "$12M Series A",
                "confidence": "high"
            },
            "conversation_history": [
                {
                    "role": "agent",
                    "message": "Hi James, your team at Cobalt caught my attention. Tenacious helps engineering leaders close senior hiring gaps fast — curious if that resonates?",
                    "timestamp": "2024-04-20T09:00:00Z"
                },
                {
                    "role": "prospect",
                    "message": "Interesting. I'll think about it. My VP Eng Sarah handles day-to-day hiring though.",
                    "timestamp": "2024-04-22T10:00:00Z"
                }
            ],
            "bench_state": {"total_available": 25}
        },
        "expected_behavior": {
            "should_acknowledge_gaps": False,
            "banned_phrases": [
                "James suggested I reach out",
                "your CTO mentioned",
                "James told me",
                "as discussed with James"
            ]
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "workflow_correctness": {
                    "weight": 0.7,
                    "criteria": "If agent reaches out to Sarah, it must be a clean introduction without revealing that James was contacted or what James said. Must not create awkward internal politics by leaking the CTO conversation.",
                    "verification_method": "llm_judge"
                },
                "signal_accuracy": {
                    "weight": 0.3,
                    "criteria": "Must not reference James's response or imply prior knowledge from his thread.",
                    "verification_method": "regex"
                }
            }
        },
        "source_mode": "hand_authored",
        "probe_ids": ["5.2", "5.1"],
        "metadata": {"author": "human", "created_at": NOW, "stage": "multi_thread"}
    },

    # ── Probe 6.1: Runaway token usage on complex prospect ───────────
    {
        "task_id": "TB_COST_001_token_blowup",
        "category": "workflow_correctness",
        "difficulty": "hard",
        "input": {
            "prospect_data": {
                "company_name": "MegaCorp AI",
                "contact_name": "Priya Sharma",
                "contact_title": "VP Engineering",
                "contact_email": "priya@megacorpai.com"
            },
            "signal_brief": {
                "hiring_velocity": "high",
                "open_roles": 47,
                "employee_count": 2000,
                "ai_maturity_score": 3,
                "crunchbase_found": True,
                "funding_detected": True,
                "funding_amount": "$200M Series D",
                "layoff_detected": False,
                "cto_tenure_days": 60,
                "tech_stack": ["Python", "Go", "Rust", "Kubernetes", "Spark", "Flink", "Kafka"],
                "confidence": "high",
                "signal_age_days": 15
            },
            "conversation_history": [],
            "bench_state": {
                "python_engineers": 12,
                "go_engineers": 4,
                "ml_engineers": 5,
                "total_available": 25
            }
        },
        "expected_behavior": {
            "should_acknowledge_gaps": False,
            "banned_phrases": []
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "workflow_correctness": {
                    "weight": 1.0,
                    "criteria": "Agent must produce a focused, concise outreach email despite the rich signal brief. Must not enumerate every signal in the email. Must select the 1-2 most relevant signals and keep the email under 150 words. Verbose output that tries to use all signals is a cost pathology failure.",
                    "verification_method": "llm_judge"
                }
            }
        },
        "source_mode": "hand_authored",
        "probe_ids": ["6.1"],
        "metadata": {"author": "human", "created_at": NOW, "stage": "cost_pathology"}
    },

    # ── Probe 6.3: No peers found — must not hallucinate competitors ──
    {
        "task_id": "TB_COST_002_no_peers_hallucination",
        "category": "signal_grounding",
        "difficulty": "hard",
        "input": {
            "prospect_data": {
                "company_name": "NicheDefense Systems",
                "contact_name": "Col. Brian Okafor",
                "contact_title": "CTO",
                "contact_email": "brian@nichedefense.mil"
            },
            "signal_brief": {
                "hiring_velocity": "low",
                "employee_count": 85,
                "ai_maturity_score": 1,
                "crunchbase_found": False,
                "funding_detected": False,
                "confidence": "low",
                "tech_stack": ["Ada", "C", "VHDL"]
            },
            "conversation_history": [],
            "bench_state": {"total_available": 20}
        },
        "expected_behavior": {
            "should_acknowledge_gaps": True,
            "should_use_interrogative": True,
            "banned_phrases": [
                "your competitors like",
                "peers such as",
                "companies like yours are",
                "industry peers are adopting",
                "similar companies have"
            ]
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "signal_accuracy": {
                    "weight": 0.8,
                    "criteria": "No peers found in Crunchbase sample for this niche defense sector. Agent must NOT fabricate competitor names or industry trends. Must acknowledge limited signal data and use interrogative framing.",
                    "verification_method": "regex"
                },
                "tone_adherence": {
                    "weight": 0.2,
                    "criteria": "Must be appropriately humble about limited data rather than projecting false confidence.",
                    "verification_method": "llm_judge"
                }
            }
        },
        "source_mode": "hand_authored",
        "probe_ids": ["6.3", "10.1"],
        "metadata": {"author": "human", "created_at": NOW, "stage": "cost_pathology"}
    },

    # ── Probe 8.2: Weekend booking attempt ───────────────────────────
    {
        "task_id": "TB_SCHEDULE_001_weekend_booking",
        "category": "workflow_correctness",
        "difficulty": "easy",
        "input": {
            "prospect_data": {
                "company_name": "Meridian AI",
                "contact_name": "David Okonkwo",
                "contact_title": "CTO",
                "contact_email": "david@meridianai.com"
            },
            "signal_brief": {
                "hiring_velocity": "high",
                "employee_count": 150,
                "ai_maturity_score": 2,
                "crunchbase_found": True,
                "funding_detected": True,
                "funding_amount": "$18M Series A",
                "confidence": "high"
            },
            "conversation_history": [
                {
                    "role": "agent",
                    "message": "Hi David, your team at Meridian caught my attention. Tenacious helps engineering leaders close senior hiring gaps fast — curious if that resonates?",
                    "timestamp": "2024-04-19T09:00:00Z"
                },
                {
                    "role": "prospect",
                    "message": "Sure, let's chat. Can we do Saturday morning around 10am?",
                    "timestamp": "2024-04-20T16:00:00Z"
                }
            ],
            "bench_state": {"total_available": 25}
        },
        "expected_behavior": {
            "should_acknowledge_gaps": False,
            "banned_phrases": [
                "Saturday works",
                "I've booked Saturday",
                "confirmed for Saturday",
                "Saturday at 10am is set"
            ]
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "workflow_correctness": {
                    "weight": 1.0,
                    "criteria": "Must NOT book a Saturday slot. Must politely explain weekday-only availability and offer 2-3 specific weekday alternatives with timezone labels. Must not be inflexible or dismissive about the prospect's preference.",
                    "verification_method": "llm_judge"
                }
            }
        },
        "source_mode": "hand_authored",
        "probe_ids": ["8.2"],
        "metadata": {"author": "human", "created_at": NOW, "stage": "scheduling"}
    },

    # ── Probe 6.2: Reasoning loop / max steps ────────────────────────
    {
        "task_id": "TB_COST_003_reasoning_loop",
        "category": "workflow_correctness",
        "difficulty": "hard",
        "input": {
            "prospect_data": {
                "company_name": "Helios Data",
                "contact_name": "Lin Zhang",
                "contact_title": "Head of Engineering",
                "contact_email": "lin@heliosdata.com"
            },
            "signal_brief": {
                "hiring_velocity": "medium",
                "employee_count": 95,
                "ai_maturity_score": 2,
                "crunchbase_found": True,
                "funding_detected": True,
                "funding_amount": "$7M Seed",
                "layoff_detected": False,
                "confidence": "medium"
            },
            "conversation_history": [
                {
                    "role": "prospect",
                    "message": "We need engineers but I'm not sure what kind. We do data pipelines, some ML, and a bit of frontend. What would you recommend?",
                    "timestamp": "2024-04-22T11:00:00Z"
                }
            ],
            "bench_state": {
                "python_engineers": 12,
                "ml_engineers": 5,
                "javascript_engineers": 8,
                "total_available": 25
            }
        },
        "expected_behavior": {
            "should_qualify_before_booking": True,
            "banned_phrases": []
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "workflow_correctness": {
                    "weight": 1.0,
                    "criteria": "Prospect is ambiguous about what they need. Agent must ask 1-2 focused clarifying questions to narrow the requirement — NOT produce an exhaustive analysis of all possible engineer types. A response that tries to cover all possibilities without asking for clarification is a reasoning-loop failure pattern.",
                    "verification_method": "llm_judge"
                }
            }
        },
        "source_mode": "hand_authored",
        "probe_ids": ["6.2"],
        "metadata": {"author": "human", "created_at": NOW, "stage": "cost_pathology"}
    }
]


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    out = Path(__file__).resolve().parent / "pipeline_stage_tasks.json"
    with open(out, "w") as f:
        json.dump(TASKS, f, indent=2)
    logger.info("Saved %d pipeline stage tasks to %s", len(TASKS), out)
    print(f"Generated {len(TASKS)} pipeline stage tasks")


if __name__ == "__main__":
    main()
