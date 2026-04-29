#!/usr/bin/env python3
"""
Trace-Derived Tasks for Tenacious-Bench.
Each real Week 10 trace pattern expanded into task variants.

Trace patterns:
  - 7a52cdcf (turns 3,5,7): multi-turn tone drift across gap analysis
  - c0033ad8 + 850154ee:    AI maturity scoring inconsistency
  - c0033ad8_4:             ambiguous segment → n/a classification
  - 1d816fd2_2:             cost pathology (7,314 tokens, 4x normal)
  - c0033ad8_5:             subject line 73 chars (fails 60-char limit)
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
NOW = datetime.now(timezone.utc).isoformat()

# ── Shared prospect pool (varied to avoid n-gram overlap) ─────────────
PROSPECTS = [
    {"company_name": "Meridian AI",      "contact_name": "Priya Sharma",   "contact_title": "VP Engineering",    "contact_email": "priya@meridianai.com"},
    {"company_name": "NovaCraft",        "contact_name": "David Okonkwo",  "contact_title": "CTO",               "contact_email": "david@novacraft.io"},
    {"company_name": "Helios Data",      "contact_name": "Lin Zhang",      "contact_title": "Head of Engineering","contact_email": "lin@heliosdata.com"},
    {"company_name": "Stratos Systems",  "contact_name": "Rachel Torres",  "contact_title": "VP Platform",       "contact_email": "rachel@stratossystems.com"},
    {"company_name": "Cobalt Labs",      "contact_name": "James Mwangi",   "contact_title": "CTO",               "contact_email": "james@cobaltlabs.dev"},
    {"company_name": "Apex Fintech",     "contact_name": "Nadia Okonkwo",  "contact_title": "CTO",               "contact_email": "nadia@apexfintech.com"},
    {"company_name": "Luminary Tech",    "contact_name": "Kwame Asante",   "contact_title": "VP Engineering",    "contact_email": "kwame@luminarytech.com"},
    {"company_name": "Vortex Analytics", "contact_name": "Ingrid Larsson", "contact_title": "CTO",               "contact_email": "ingrid@vortexanalytics.se"},
    {"company_name": "Quantum Leap AI",  "contact_name": "Marcus Webb",    "contact_title": "Head of Engineering","contact_email": "marcus@quantumleapai.com"},
    {"company_name": "Nexus AI",         "contact_name": "Chioma Eze",     "contact_title": "VP Engineering",    "contact_email": "chioma@nexusai.com"},
]

BANNED_TONE = ["leverage", "synergy", "best-in-class", "world-class", "cutting-edge",
               "just following up", "circling back", "touching base"]

def p(i): return PROSPECTS[i % len(PROSPECTS)]


# ════════════════════════════════════════════════════════════════════
# PATTERN 1: Multi-turn tone drift (trace 7a52cdcf turns 3→5→7)
# Evidence: professional tone in turn 1, marketing drift by turn 4
# ════════════════════════════════════════════════════════════════════

def tone_drift_tasks() -> list[dict]:
    tasks = []

    # Variant 1: 2-turn — tone must hold after first prospect reply
    pr = p(0)
    tasks.append({
        "task_id": "TB_TRACE_001_tone_drift_2turn",
        "category": "tone_consistency",
        "difficulty": "easy",
        "input": {
            "prospect_data": pr,
            "signal_brief": {"hiring_velocity": "high", "employee_count": 200,
                             "ai_maturity_score": 2, "funding_detected": True,
                             "funding_amount": "$20M Series B", "confidence": "high"},
            "conversation_history": [
                {"role": "agent",
                 "message": f"Hi {pr['contact_name'].split()[0]}, noticed {pr['company_name']} has been scaling its engineering team. Tenacious places senior engineers at companies at your stage — is augmenting your team something you're exploring?",
                 "timestamp": "2026-04-25T10:59:33Z"},
                {"role": "prospect",
                 "message": "Interesting. Tell me more about what you do.",
                 "timestamp": "2026-04-25T10:59:56Z"},
            ],
            "bench_state": {"python_engineers": 12, "ml_engineers": 5, "total_available": 25},
        },
        "expected_behavior": {
            "max_subject_length": 60,
            "banned_phrases": BANNED_TONE,
            "required_tone_markers": ["direct", "professional"],
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "tone_adherence": {
                    "weight": 1.0,
                    "criteria": "Turn 2 response must maintain the same direct, grounded tone as turn 1. Must not drift into marketing language or banned phrases when asked to elaborate.",
                    "verification_method": "regex",
                }
            },
        },
        "source_mode": "trace_derived",
        "probe_ids": ["4.1"],
        "metadata": {"author": "trace", "created_at": NOW,
                     "trace_ids": ["llm_gap_analysis_7a52cdcf_3", "llm_gap_analysis_7a52cdcf_5"]},
    })

    # Variant 2: 4-turn — tone must hold through extended conversation
    pr = p(1)
    tasks.append({
        "task_id": "TB_TRACE_002_tone_drift_4turn",
        "category": "tone_consistency",
        "difficulty": "medium",
        "input": {
            "prospect_data": pr,
            "signal_brief": {"hiring_velocity": "high", "employee_count": 300,
                             "ai_maturity_score": 3, "funding_detected": True,
                             "funding_amount": "$35M Series B", "confidence": "high"},
            "conversation_history": [
                {"role": "agent",
                 "message": f"Hi {pr['contact_name'].split()[0]}, your team at {pr['company_name']} caught my attention. Tenacious helps engineering leaders close senior hiring gaps fast — curious if that resonates?",
                 "timestamp": "2026-04-25T10:00:00Z"},
                {"role": "prospect",
                 "message": "We might be interested. What kind of engineers do you place?",
                 "timestamp": "2026-04-25T10:05:00Z"},
                {"role": "agent",
                 "message": "We focus on senior engineers across Python, ML, Go, and JavaScript. Typically 5+ years experience, vetted for technical depth.",
                 "timestamp": "2026-04-25T10:06:00Z"},
                {"role": "prospect",
                 "message": "OK. And what makes you different from other staffing firms?",
                 "timestamp": "2026-04-25T10:10:00Z"},
            ],
            "bench_state": {"python_engineers": 12, "ml_engineers": 5, "total_available": 25},
        },
        "expected_behavior": {
            "max_subject_length": 60,
            "banned_phrases": BANNED_TONE + ["unlike other firms", "we're the best", "industry-leading"],
            "required_tone_markers": ["direct", "professional"],
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "tone_adherence": {
                    "weight": 1.0,
                    "criteria": "Turn 4 response to differentiation question must remain grounded and factual. Must not drift into superlatives or competitor disparagement. Evidence from trace 7a52cdcf_7: tone degraded by turn 4.",
                    "verification_method": "regex",
                }
            },
        },
        "source_mode": "trace_derived",
        "probe_ids": ["4.1"],
        "metadata": {"author": "trace", "created_at": NOW,
                     "trace_ids": ["llm_gap_analysis_7a52cdcf_7"]},
    })

    # Variants 3-8: different turn counts, different drift triggers
    drift_triggers = [
        (3, "What's your success rate?",         "medium", p(2), "4.1"),
        (4, "Can you guarantee quality?",         "hard",   p(3), "4.1"),
        (5, "Why should I trust you?",            "hard",   p(4), "4.3"),
        (6, "Our last vendor was terrible.",      "hard",   p(5), "4.3"),
        (7, "I've heard mixed things about you.", "hard",   p(6), "4.1"),
        (8, "What do your clients say about you?","medium", p(7), "4.1"),
    ]

    for i, (turn_n, trigger, diff, pr, probe) in enumerate(drift_triggers):
        history = [
            {"role": "agent",
             "message": f"Hi {pr['contact_name'].split()[0]}, noticed {pr['company_name']} has several open engineering roles. Tenacious specializes in placing senior engineers for teams at your scale — would it be worth a quick conversation?",
             "timestamp": "2026-04-25T10:00:00Z"},
        ]
        for t in range(1, turn_n - 1):
            filler_q = ["Tell me more.", "Interesting, go on.", "What else?", "Keep going."][t % 4]
            filler_a = [
                "We place senior engineers vetted for technical depth and communication skills.",
                "Our bench covers Python, ML, Go, and JavaScript — typically 5+ years experience.",
                "We focus on engineers who can contribute from day one with minimal ramp-up.",
                "Tenacious vets for both technical depth and cultural fit with your team.",
            ][t % 4]
            history.append({"role": "prospect", "message": filler_q,
                            "timestamp": f"2026-04-25T10:0{t}:00Z"})
            history.append({"role": "agent", "message": filler_a,
                            "timestamp": f"2026-04-25T10:0{t+1}:00Z"})
        history.append({"role": "prospect", "message": trigger,
                        "timestamp": f"2026-04-25T10:{turn_n:02d}:00Z"})

        tasks.append({
            "task_id": f"TB_TRACE_{3+i:03d}_tone_drift_{turn_n}turn",
            "category": "tone_consistency",
            "difficulty": diff,
            "input": {
                "prospect_data": pr,
                "signal_brief": {"hiring_velocity": "medium", "employee_count": 150,
                                 "ai_maturity_score": 2, "confidence": "medium"},
                "conversation_history": history,
                "bench_state": {"python_engineers": 12, "total_available": 20},
            },
            "expected_behavior": {
                "max_subject_length": 60,
                "banned_phrases": BANNED_TONE + ["guaranteed", "we're the best", "unlike others"],
            },
            "scoring_rubric": {
                "pass_threshold": 0.7,
                "dimensions": {
                    "tone_adherence": {
                        "weight": 1.0,
                        "criteria": f"Turn {turn_n} response to '{trigger}' must remain direct and grounded. Must not drift into defensive, superlative, or marketing language under pressure.",
                        "verification_method": "regex",
                    }
                },
            },
            "source_mode": "trace_derived",
            "probe_ids": [probe],
            "metadata": {"author": "trace", "created_at": NOW,
                         "trace_ids": ["llm_gap_analysis_7a52cdcf_7"]},
        })

    return tasks


# ════════════════════════════════════════════════════════════════════
# PATTERN 2: AI maturity inconsistency (traces c0033ad8_3, 850154ee_1)
# Evidence: similar inputs → different confidence scores
# ════════════════════════════════════════════════════════════════════

def ai_maturity_tasks() -> list[dict]:
    tasks = []

    maturity_scenarios = [
        # (score, evidence_strength, expected_phrasing, difficulty, probe)
        (0, "no AI roles, no AI blog posts, no AI stack",    "interrogative", "easy",   "2.2"),
        (1, "one blog post mentioning AI, no AI roles",      "interrogative", "easy",   "2.2"),
        (2, "2 ML engineers, one AI product feature",        "assertive",     "medium", "2.1"),
        (3, "dedicated ML team, AI-first product, MLOps",    "assertive",     "medium", "2.1"),
        (0, "JS career page — hiring data unavailable",      "interrogative", "hard",   "9.2"),
        (1, "single AI mention in job description",          "interrogative", "medium", "2.2"),
        (2, "AI maturity inferred from tech stack only",     "hedged",        "hard",   "2.1"),
        (3, "strong AI signal but 200-day-old data",         "interrogative", "hard",   "9.1"),
    ]

    for i, (score, evidence, phrasing, diff, probe) in enumerate(maturity_scenarios):
        pr = p(i)
        banned = (["you are clearly", "you definitely have", "your AI team is"]
                  if phrasing == "interrogative" else
                  ["it looks like you might", "possibly", "we're not sure"])

        tasks.append({
            "task_id": f"TB_TRACE_{9+i:03d}_ai_maturity_{i+1:02d}_score{score}",
            "category": "signal_grounding",
            "difficulty": diff,
            "input": {
                "prospect_data": pr,
                "signal_brief": {
                    "ai_maturity_score": score,
                    "hiring_velocity": "medium",
                    "employee_count": 150,
                    "crunchbase_found": True,
                    "funding_detected": True,
                    "funding_amount": "$15M Series A",
                    "confidence": "low" if phrasing == "interrogative" else "high",
                    "signal_age_days": 200 if "200-day" in evidence else 30,
                },
                "conversation_history": [],
                "bench_state": {"ml_engineers": 5, "total_available": 20},
            },
            "expected_behavior": {
                "should_use_interrogative": phrasing == "interrogative",
                "should_flag_staleness": "200-day" in evidence,
                "banned_phrases": banned,
            },
            "scoring_rubric": {
                "pass_threshold": 0.7,
                "dimensions": {
                    "signal_accuracy": {
                        "weight": 0.7,
                        "criteria": f"AI maturity score is {score} based on: {evidence}. Agent must use {'interrogative' if phrasing == 'interrogative' else 'appropriately confident'} phrasing. Evidence from traces c0033ad8_3 and 850154ee_1: similar inputs produced different confidence levels.",
                        "verification_method": "regex",
                    },
                    "tone_adherence": {
                        "weight": 0.3,
                        "criteria": "Phrasing confidence must match signal strength — weak evidence requires hedged language.",
                        "verification_method": "llm_judge",
                    },
                },
            },
            "source_mode": "trace_derived",
            "probe_ids": [probe],
            "metadata": {"author": "trace", "created_at": NOW,
                         "trace_ids": ["llm_ai_maturity_c0033ad8_3", "llm_ai_maturity_850154ee_1"]},
        })

    return tasks


# ════════════════════════════════════════════════════════════════════
# PATTERN 3: Ambiguous segment → n/a (trace c0033ad8_4)
# Evidence: funding=False, layoff=True, ai_maturity=0 → segment n/a
# ════════════════════════════════════════════════════════════════════

def ambiguous_segment_tasks() -> list[dict]:
    tasks = []

    ambiguous_scenarios = [
        # (funding, layoff, ai_maturity, employee_count, expected_action, difficulty)
        (False, True,  0, 80,  "disengage_or_seg2_only", "hard"),
        (False, False, 0, 30,  "disengage_too_small",    "medium"),
        (True,  True,  1, 200, "seg2_not_seg1",          "hard"),
        (False, False, 1, 45,  "disengage_too_small",    "medium"),
        (True,  False, 0, 60,  "seg1_with_caution",      "medium"),
        (False, True,  2, 150, "seg2_restructuring",     "hard"),
        (True,  True,  3, 500, "seg2_not_seg4",          "hard"),
        (False, False, 2, 25,  "disengage_too_small",    "medium"),
    ]

    for i, (funding, layoff, ai_mat, emp, action, diff) in enumerate(ambiguous_scenarios):
        pr = p(i)
        banned_by_action = {
            "disengage_or_seg2_only": ["scale your team", "grow your engineering", "hire faster"],
            "disengage_too_small":    ["vendor reassessment", "your current vendors", "scale fast"],
            "seg2_not_seg1":          ["scale fast with fresh budget", "accelerate hiring", "grow aggressively"],
            "seg1_with_caution":      ["after your restructuring", "given your layoffs"],
            "seg2_restructuring":     ["scale your team", "hire aggressively", "grow fast"],
            "seg2_not_seg4":          ["your AI capability gap", "falling behind on AI"],
        }.get(action, [])

        tasks.append({
            "task_id": f"TB_TRACE_{17+i:03d}_ambiguous_segment_{action[:12]}",
            "category": "workflow_correctness",
            "difficulty": diff,
            "input": {
                "prospect_data": pr,
                "signal_brief": {
                    "funding_detected": funding,
                    "funding_amount": "$10M Series A" if funding else None,
                    "layoff_detected": layoff,
                    "layoff_percentage": 20 if layoff else 0,
                    "ai_maturity_score": ai_mat,
                    "employee_count": emp,
                    "hiring_velocity": "low" if layoff else "medium",
                    "crunchbase_found": True,
                    "confidence": "medium",
                },
                "conversation_history": [],
                "bench_state": {"total_available": 20},
            },
            "expected_behavior": {
                "should_acknowledge_gaps": layoff or emp < 50,
                "banned_phrases": banned_by_action,
            },
            "scoring_rubric": {
                "pass_threshold": 0.7,
                "dimensions": {
                    "workflow_correctness": {
                        "weight": 0.7,
                        "criteria": f"Mixed signals: funding={funding}, layoff={layoff}, ai_maturity={ai_mat}, employees={emp}. Expected routing: {action}. Evidence from trace c0033ad8_4: agent correctly classified as n/a when signals were ambiguous.",
                        "verification_method": "llm_judge",
                    },
                    "tone_adherence": {
                        "weight": 0.3,
                        "criteria": "Must not use tone-deaf language given the signal combination.",
                        "verification_method": "regex",
                    },
                },
            },
            "source_mode": "trace_derived",
            "probe_ids": ["1.1", "1.4"],
            "metadata": {"author": "trace", "created_at": NOW,
                         "trace_ids": ["out_enrichment_complete_c0033ad8_4"]},
        })

    return tasks


# ════════════════════════════════════════════════════════════════════
# PATTERN 4: Cost pathology (trace 1d816fd2_2 — 7,314 tokens, 4x normal)
# Evidence: complex prospect triggers verbose output
# ════════════════════════════════════════════════════════════════════

def cost_pathology_tasks() -> list[dict]:
    tasks = []

    complex_briefs = [
        {"open_roles": 45, "tech_stack": ["Python","Go","Rust","Kafka","Spark"],
         "funding_amount": "$200M Series D", "employee_count": 2000, "ai_maturity_score": 3},
        {"open_roles": 30, "tech_stack": ["Java","Scala","Kubernetes","Flink"],
         "funding_amount": "$80M Series C",  "employee_count": 800,  "ai_maturity_score": 2},
        {"open_roles": 20, "tech_stack": ["Python","PyTorch","CUDA","C++"],
         "funding_amount": "$50M Series B",  "employee_count": 400,  "ai_maturity_score": 3},
        {"open_roles": 15, "tech_stack": ["Elixir","Phoenix","PostgreSQL","Redis"],
         "funding_amount": "$25M Series A",  "employee_count": 200,  "ai_maturity_score": 2},
        {"open_roles": 12, "tech_stack": ["Rust","WebAssembly","WASM","C"],
         "funding_amount": "$15M Seed",      "employee_count": 100,  "ai_maturity_score": 1},
    ]

    for i, brief in enumerate(complex_briefs):
        pr = p(i)
        tasks.append({
            "task_id": f"TB_TRACE_{25+i:03d}_cost_pathology_complex{i+1}",
            "category": "workflow_correctness",
            "difficulty": "hard",
            "input": {
                "prospect_data": pr,
                "signal_brief": {
                    **brief,
                    "hiring_velocity": "high",
                    "crunchbase_found": True,
                    "funding_detected": True,
                    "layoff_detected": False,
                    "confidence": "high",
                    "signal_age_days": 15,
                },
                "conversation_history": [],
                "bench_state": {"python_engineers": 12, "ml_engineers": 5, "total_available": 25},
            },
            "expected_behavior": {
                "should_acknowledge_gaps": False,
                "banned_phrases": [],
            },
            "scoring_rubric": {
                "pass_threshold": 0.7,
                "dimensions": {
                    "workflow_correctness": {
                        "weight": 1.0,
                        "criteria": f"Rich signal brief with {len(brief['tech_stack'])} stack items and {brief['open_roles']} open roles. Agent must produce a focused email under 150 words using only the 1-2 most relevant signals. Evidence from trace 1d816fd2_2: 7,314 tokens (4x normal) when agent tried to use all signals.",
                        "verification_method": "llm_judge",
                    }
                },
            },
            "source_mode": "trace_derived",
            "probe_ids": ["6.1"],
            "metadata": {"author": "trace", "created_at": NOW,
                         "trace_ids": ["llm_gap_analysis_1d816fd2_2"]},
        })

    return tasks


# ════════════════════════════════════════════════════════════════════
# PATTERN 5: Subject line failure (trace c0033ad8_5 — 73 chars)
# Evidence: "Request: Exploring technical SEO partnerships post-restructuring"
# ════════════════════════════════════════════════════════════════════

def subject_line_tasks() -> list[dict]:
    tasks = []

    # Scenarios that tempt the agent to write long subject lines
    tempting_scenarios = [
        ("post-layoff company with new CTO and Series B funding",          "hard",   p(0), ["4.5"]),
        ("company with 3 active signals: funding, hiring, AI maturity",    "hard",   p(1), ["4.5"]),
        ("prospect who asked about specific tech stack and timeline",       "medium", p(2), ["4.5"]),
        ("follow-up after prospect mentioned budget constraints",           "medium", p(3), ["4.5", "4.2"]),
        ("company in regulated sector with compliance requirements",        "hard",   p(4), ["4.5", "10.3"]),
        ("prospect who mentioned competitor by name in previous turn",      "hard",   p(5), ["4.5", "4.1"]),
        ("warm reply after 7-day silence — re-engagement email",           "medium", p(6), ["4.5", "4.2"]),
        ("multi-signal brief: layoff + new CTO + AI maturity 3",           "hard",   p(7), ["4.5", "1.4"]),
        ("prospect asked for case study and reference in same message",     "medium", p(8), ["4.5"]),
        ("scope change: prospect pivoted from Python to Rust engineers",    "hard",   p(9), ["4.5", "3.3"]),
    ]

    for i, (scenario, diff, pr, probes) in enumerate(tempting_scenarios):
        tasks.append({
            "task_id": f"TB_TRACE_{30+i:03d}_subject_line_{i+1}",
            "category": "tone_consistency",
            "difficulty": diff,
            "input": {
                "prospect_data": pr,
                "signal_brief": {
                    "hiring_velocity": "high",
                    "employee_count": 200,
                    "ai_maturity_score": 2,
                    "funding_detected": True,
                    "funding_amount": "$20M Series B",
                    "crunchbase_found": True,
                    "confidence": "high",
                },
                "conversation_history": [],
                "bench_state": {"python_engineers": 12, "total_available": 20},
            },
            "expected_behavior": {
                "max_subject_length": 60,
                "banned_phrases": BANNED_TONE,
            },
            "scoring_rubric": {
                "pass_threshold": 0.7,
                "dimensions": {
                    "tone_adherence": {
                        "weight": 1.0,
                        "criteria": f"Scenario: {scenario}. Subject line must be <=60 characters despite the temptation to include multiple signals. Evidence from trace c0033ad8_5: agent generated 73-char subject 'Request: Exploring technical SEO partnerships post-restructuring'.",
                        "verification_method": "regex",
                    }
                },
            },
            "source_mode": "trace_derived",
            "probe_ids": probes,
            "metadata": {"author": "trace", "created_at": NOW,
                         "trace_ids": ["out_email_send_c0033ad8_5"]},
        })

    return tasks


def generate_all() -> list[dict]:
    tone   = tone_drift_tasks()        # 8 tasks
    ai_mat = ai_maturity_tasks()       # 8 tasks
    seg    = ambiguous_segment_tasks() # 8 tasks
    cost   = cost_pathology_tasks()    # 5 tasks
    subj   = subject_line_tasks()      # 10 tasks
    all_tasks = tone + ai_mat + seg + cost + subj
    logger.info(
        "Generated %d trace-derived tasks: tone=%d, ai_maturity=%d, segment=%d, cost=%d, subject=%d",
        len(all_tasks), len(tone), len(ai_mat), len(seg), len(cost), len(subj),
    )
    return all_tasks


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    tasks = generate_all()
    out = Path(__file__).resolve().parent / "trace_derived_tasks.json"
    with open(out, "w") as f:
        json.dump(tasks, f, indent=2)
    logger.info("Saved %d trace-derived tasks to %s", len(tasks), out)

    cats  = {}
    diffs = {}
    for t in tasks:
        cats[t["category"]]  = cats.get(t["category"], 0) + 1
        diffs[t["difficulty"]] = diffs.get(t["difficulty"], 0) + 1
    print(f"\nTotal: {len(tasks)} trace-derived tasks")
    print(f"Categories: {cats}")
    print(f"Difficulty: {diffs}")


if __name__ == "__main__":
    main()
