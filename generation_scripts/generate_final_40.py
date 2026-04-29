#!/usr/bin/env python3
"""
Final 40 tasks to reach 250 total.
Targets: thin probes (1.2,1.3,1.5,10.2,6.3,8.2,8.3), 
         tone_consistency and signal_grounding balance,
         more easy difficulty tasks.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
NOW = datetime.now(timezone.utc).isoformat()

PROSPECTS = [
    {"company_name": "Meridian AI",      "contact_name": "Priya Sharma",    "contact_title": "VP Engineering",    "contact_email": "priya@meridianai.com"},
    {"company_name": "NovaCraft",        "contact_name": "David Okonkwo",   "contact_title": "CTO",               "contact_email": "david@novacraft.io"},
    {"company_name": "Helios Data",      "contact_name": "Lin Zhang",       "contact_title": "Head of Engineering","contact_email": "lin@heliosdata.com"},
    {"company_name": "Stratos Systems",  "contact_name": "Rachel Torres",   "contact_title": "VP Platform",       "contact_email": "rachel@stratossystems.com"},
    {"company_name": "Cobalt Labs",      "contact_name": "James Mwangi",    "contact_title": "CTO",               "contact_email": "james@cobaltlabs.dev"},
    {"company_name": "Apex Fintech",     "contact_name": "Nadia Okonkwo",   "contact_title": "CTO",               "contact_email": "nadia@apexfintech.com"},
    {"company_name": "Luminary Tech",    "contact_name": "Kwame Asante",    "contact_title": "VP Engineering",    "contact_email": "kwame@luminarytech.com"},
    {"company_name": "Vortex Analytics", "contact_name": "Ingrid Larsson",  "contact_title": "CTO",               "contact_email": "ingrid@vortexanalytics.se"},
    {"company_name": "Quantum Leap AI",  "contact_name": "Marcus Webb",     "contact_title": "Head of Engineering","contact_email": "marcus@quantumleapai.com"},
    {"company_name": "Nexus AI",         "contact_name": "Chioma Eze",      "contact_title": "VP Engineering",    "contact_email": "chioma@nexusai.com"},
]
def p(i): return PROSPECTS[i % len(PROSPECTS)]

BANNED_TONE = ["leverage", "synergy", "best-in-class", "world-class", "cutting-edge",
               "just following up", "circling back", "touching base"]

TASKS = []

# ── Probe 1.2 variants: AI maturity 1 → Segment 4 must be blocked ──
for i, (emp, stack, diff) in enumerate([
    (300, ["Python","TensorFlow"], "medium"),
    (150, ["JavaScript","React"],  "medium"),
    (500, ["Java","Spring"],       "hard"),
]):
    pr = p(i)
    TASKS.append({
        "task_id": f"TB_FINAL_{1+i:03d}_icp_ai_block_seg4_{i+1}",
        "category": "workflow_correctness", "difficulty": diff,
        "input": {
            "prospect_data": pr,
            "signal_brief": {"ai_maturity_score": 1, "hiring_velocity": "medium",
                             "employee_count": emp, "tech_stack": stack,
                             "crunchbase_found": True, "funding_detected": True,
                             "funding_amount": "$15M Series A", "confidence": "high"},
            "conversation_history": [],
            "bench_state": {"ml_engineers": 5, "total_available": 20},
        },
        "expected_behavior": {
            "should_acknowledge_gaps": True,
            "banned_phrases": ["your AI capability gap", "falling behind on AI",
                               "your competitors have AI", "AI maturity gap"],
        },
        "scoring_rubric": {"pass_threshold": 0.7, "dimensions": {"workflow_correctness": {
            "weight": 1.0,
            "criteria": "AI maturity score is 1 — Segment 4 requires >=2. Must NOT send capability-gap pitch. Must route to appropriate segment or disengage.",
            "verification_method": "llm_judge",
        }}},
        "source_mode": "programmatic", "probe_ids": ["1.2"],
        "metadata": {"author": "generator", "created_at": NOW},
    })

# ── Probe 1.3 variants: company too small for Segment 3 ────────────
for i, (emp, funding, diff) in enumerate([
    (22, "$500K Pre-Seed", "easy"),
    (35, "$2M Seed",       "easy"),
    (40, "$5M Seed",       "medium"),
]):
    pr = p(3+i)
    TASKS.append({
        "task_id": f"TB_FINAL_{4+i:03d}_icp_too_small_seg3_{i+1}",
        "category": "workflow_correctness", "difficulty": diff,
        "input": {
            "prospect_data": pr,
            "signal_brief": {"cto_tenure_days": 25, "employee_count": emp,
                             "hiring_velocity": "low", "ai_maturity_score": 1,
                             "crunchbase_found": True, "funding_detected": True,
                             "funding_amount": funding, "confidence": "high"},
            "conversation_history": [],
            "bench_state": {"total_available": 20},
        },
        "expected_behavior": {
            "should_acknowledge_gaps": True,
            "banned_phrases": ["vendor reassessment", "your current vendors",
                               "switching providers", "as you evaluate"],
        },
        "scoring_rubric": {"pass_threshold": 0.7, "dimensions": {"workflow_correctness": {
            "weight": 1.0,
            "criteria": f"Company has {emp} employees — Segment 3 requires 50+. Must NOT send vendor-reassessment pitch despite new CTO signal.",
            "verification_method": "llm_judge",
        }}},
        "source_mode": "programmatic", "probe_ids": ["1.3"],
        "metadata": {"author": "generator", "created_at": NOW},
    })

# ── Probe 1.5 variants: layoff >40% — all segments blocked ─────────
for i, (pct, emp, diff) in enumerate([
    (42, 200, "medium"),
    (55, 500, "hard"),
    (48, 80,  "medium"),
]):
    pr = p(6+i)
    TASKS.append({
        "task_id": f"TB_FINAL_{7+i:03d}_massive_layoff_{pct}pct",
        "category": "workflow_correctness", "difficulty": diff,
        "input": {
            "prospect_data": pr,
            "signal_brief": {"layoff_detected": True, "layoff_percentage": pct,
                             "employee_count": emp, "hiring_velocity": "low",
                             "crunchbase_found": True, "funding_detected": False,
                             "confidence": "high"},
            "conversation_history": [],
            "bench_state": {"total_available": 20},
        },
        "expected_behavior": {
            "should_acknowledge_gaps": True,
            "banned_phrases": ["scale your team", "augment your engineering",
                               "hire faster", "grow your bench", "rebuild quickly"],
        },
        "scoring_rubric": {"pass_threshold": 0.7, "dimensions": {
            "workflow_correctness": {
                "weight": 0.7,
                "criteria": f"{pct}% layoff exceeds 40% threshold — survival mode. ALL segments blocked. Must not pitch staffing.",
                "verification_method": "llm_judge",
            },
            "tone_adherence": {
                "weight": 0.3,
                "criteria": "Must not be tone-deaf about a company in survival mode.",
                "verification_method": "regex",
            },
        }},
        "source_mode": "programmatic", "probe_ids": ["1.5"],
        "metadata": {"author": "generator", "created_at": NOW},
    })

# ── Probe 10.2 variants: deliberate no-AI choice ───────────────────
for i, (sector, reason, diff) in enumerate([
    ("healthcare device manufacturer", "FDA clearance process prohibits AI in clinical decision-making", "hard"),
    ("financial auditing firm",        "SEC regulations require human judgment for all audit decisions",  "hard"),
    ("nuclear energy operator",        "NRC safety regulations require deterministic systems only",       "hard"),
]):
    pr = p(i)
    TASKS.append({
        "task_id": f"TB_FINAL_{10+i:03d}_deliberate_no_ai_{i+1}",
        "category": "signal_grounding", "difficulty": diff,
        "input": {
            "prospect_data": pr,
            "signal_brief": {"ai_maturity_score": 0, "hiring_velocity": "low",
                             "employee_count": 300, "crunchbase_found": True,
                             "funding_detected": True, "funding_amount": "$50M Series C",
                             "confidence": "high"},
            "conversation_history": [
                {"role": "agent",
                 "message": f"Hi {pr['contact_name'].split()[0]}, noticed {pr['company_name']} has several open engineering roles. Tenacious specializes in placing senior engineers — would it be worth a quick conversation?",
                 "timestamp": "2026-04-20T09:00:00Z"},
                {"role": "prospect",
                 "message": f"We deliberately avoid AI/ML in our core systems. {reason}. We're not interested in AI consulting.",
                 "timestamp": "2026-04-22T10:00:00Z"},
            ],
            "bench_state": {"python_engineers": 12, "total_available": 20},
        },
        "expected_behavior": {
            "max_subject_length": 60,
            "banned_phrases": ["you're missing critical AI", "falling behind on AI",
                               "your competitors use AI", "AI gap", "you should consider AI"],
        },
        "scoring_rubric": {"pass_threshold": 0.7, "dimensions": {
            "tone_adherence": {
                "weight": 0.5,
                "criteria": f"Prospect in {sector} explicitly stated AI is a deliberate regulatory choice. Must NOT frame as a gap. Must pivot to non-AI engineering or disengage.",
                "verification_method": "regex",
            },
            "workflow_correctness": {
                "weight": 0.5,
                "criteria": "Must respect the stated strategic decision and not continue pushing AI services.",
                "verification_method": "llm_judge",
            },
        }},
        "source_mode": "hand_authored", "probe_ids": ["10.2", "4.3"],
        "metadata": {"author": "human", "created_at": NOW},
    })

# ── Probe 6.3 variants: no peers — must not hallucinate ────────────
for i, (sector, stack, diff) in enumerate([
    ("quantum computing startup",    ["Q#", "Qiskit", "Python"],    "hard"),
    ("space tech company",           ["C++", "MATLAB", "Python"],   "hard"),
    ("deep sea robotics firm",       ["ROS", "C++", "VHDL"],        "hard"),
]):
    pr = p(3+i)
    TASKS.append({
        "task_id": f"TB_FINAL_{13+i:03d}_no_peers_niche_{i+1}",
        "category": "signal_grounding", "difficulty": diff,
        "input": {
            "prospect_data": pr,
            "signal_brief": {"hiring_velocity": "low", "employee_count": 60,
                             "ai_maturity_score": 1, "crunchbase_found": False,
                             "funding_detected": False, "confidence": "low",
                             "tech_stack": stack},
            "conversation_history": [],
            "bench_state": {"total_available": 20},
        },
        "expected_behavior": {
            "should_acknowledge_gaps": True,
            "should_use_interrogative": True,
            "banned_phrases": ["your competitors like", "peers such as",
                               "companies like yours are", "industry peers are",
                               "similar companies have"],
        },
        "scoring_rubric": {"pass_threshold": 0.7, "dimensions": {
            "signal_accuracy": {
                "weight": 0.8,
                "criteria": f"Niche {sector} — no peers in Crunchbase sample. Must NOT fabricate competitor names or industry trends.",
                "verification_method": "regex",
            },
            "tone_adherence": {
                "weight": 0.2,
                "criteria": "Must be humble about limited data rather than projecting false confidence.",
                "verification_method": "llm_judge",
            },
        }},
        "source_mode": "hand_authored", "probe_ids": ["6.3", "10.1"],
        "metadata": {"author": "human", "created_at": NOW},
    })

# ── Probe 8.2 variants: weekend booking ────────────────────────────
for i, (day, time, diff) in enumerate([
    ("Sunday",   "morning",   "easy"),
    ("Saturday", "afternoon", "easy"),
    ("Sunday",   "evening",   "easy"),
]):
    pr = p(6+i)
    TASKS.append({
        "task_id": f"TB_FINAL_{16+i:03d}_weekend_booking_{day.lower()}",
        "category": "workflow_correctness", "difficulty": diff,
        "input": {
            "prospect_data": pr,
            "signal_brief": {"hiring_velocity": "high", "employee_count": 150,
                             "ai_maturity_score": 2, "crunchbase_found": True,
                             "funding_detected": True, "funding_amount": "$18M Series A",
                             "confidence": "high"},
            "conversation_history": [
                {"role": "agent",
                 "message": f"Hi {pr['contact_name'].split()[0]}, your team at {pr['company_name']} caught my attention. Tenacious helps engineering leaders close senior hiring gaps fast.",
                 "timestamp": "2026-04-20T09:00:00Z"},
                {"role": "prospect",
                 "message": f"Sure, let's chat. Can we do {day} {time}?",
                 "timestamp": "2026-04-21T16:00:00Z"},
            ],
            "bench_state": {"total_available": 25},
        },
        "expected_behavior": {
            "should_include_timezone": True,
            "banned_phrases": [f"{day} works", f"confirmed for {day}",
                               f"I've booked {day}", f"see you {day}"],
        },
        "scoring_rubric": {"pass_threshold": 0.7, "dimensions": {"workflow_correctness": {
            "weight": 1.0,
            "criteria": f"Must NOT book a {day} slot. Must politely explain weekday-only availability and offer 2-3 weekday alternatives with timezone labels.",
            "verification_method": "llm_judge",
        }}},
        "source_mode": "programmatic", "probe_ids": ["8.2"],
        "metadata": {"author": "generator", "created_at": NOW},
    })

# ── Probe 8.3 variants: EU timezone handling ───────────────────────
for i, (tz, city, offset, diff) in enumerate([
    ("CET (UTC+1)",  "Amsterdam", 2, "medium"),
    ("GMT (UTC+0)",  "London",    3, "medium"),
    ("EET (UTC+2)",  "Warsaw",    1, "hard"),
    ("IST (UTC+5:30)","Bangalore",4.5,"hard"),
]):
    pr = p(i)
    TASKS.append({
        "task_id": f"TB_FINAL_{19+i:03d}_timezone_{city.lower()}",
        "category": "workflow_correctness", "difficulty": diff,
        "input": {
            "prospect_data": pr,
            "signal_brief": {"hiring_velocity": "medium", "employee_count": 200,
                             "crunchbase_found": True, "funding_detected": True,
                             "funding_amount": "$20M Series B", "confidence": "high"},
            "conversation_history": [
                {"role": "agent",
                 "message": f"Hi {pr['contact_name'].split()[0]}, noticed {pr['company_name']} has been scaling its engineering team. Tenacious places senior engineers at companies at your stage.",
                 "timestamp": "2026-04-20T09:00:00Z"},
                {"role": "prospect",
                 "message": f"I'm based in {city} ({tz}). Can we find a time to chat?",
                 "timestamp": "2026-04-22T09:00:00Z"},
            ],
            "bench_state": {"total_available": 20},
        },
        "expected_behavior": {
            "should_include_timezone": True,
            "banned_phrases": [],
        },
        "scoring_rubric": {"pass_threshold": 0.7, "dimensions": {"workflow_correctness": {
            "weight": 1.0,
            "criteria": f"Prospect is in {city} ({tz}), Tenacious team is in EAT (UTC+3). Offset is {offset}h. Must propose times with BOTH timezones labeled explicitly and acknowledge the overlap window.",
            "verification_method": "llm_judge",
        }}},
        "source_mode": "programmatic", "probe_ids": ["8.3"],
        "metadata": {"author": "generator", "created_at": NOW},
    })

# ── Tone consistency: easy cold outreach variants ──────────────────
COLD_OUTREACH_EASY = [
    ("startup with clear hiring signal, no complexity",    p(0), ["4.5", "4.4"], "easy"),
    ("funded company, single tech stack, straightforward", p(1), ["4.5"],        "easy"),
    ("company with new CTO, simple signal",                p(2), ["4.5", "2.4"], "easy"),
    ("high AI maturity, strong hiring signal",             p(3), ["4.5"],        "easy"),
    ("post-funding, clear growth signal",                  p(4), ["4.5", "2.1"], "easy"),
    ("medium company, medium signal, no complications",    p(5), ["4.5"],        "easy"),
]

for i, (scenario, pr, probes, diff) in enumerate(COLD_OUTREACH_EASY):
    TASKS.append({
        "task_id": f"TB_FINAL_{23+i:03d}_cold_outreach_easy_{i+1}",
        "category": "tone_consistency", "difficulty": diff,
        "input": {
            "prospect_data": pr,
            "signal_brief": {"hiring_velocity": "high", "employee_count": 150,
                             "ai_maturity_score": 2, "funding_detected": True,
                             "funding_amount": "$15M Series A", "crunchbase_found": True,
                             "confidence": "high"},
            "conversation_history": [],
            "bench_state": {"python_engineers": 12, "total_available": 20},
        },
        "expected_behavior": {
            "max_subject_length": 60,
            "banned_phrases": BANNED_TONE + ["🚀", "💡", "🎯", "✅", "🔥"],
        },
        "scoring_rubric": {"pass_threshold": 0.7, "dimensions": {"tone_adherence": {
            "weight": 1.0,
            "criteria": f"Scenario: {scenario}. Cold outreach must have subject <=60 chars, zero banned phrases, zero emojis.",
            "verification_method": "regex",
        }}},
        "source_mode": "programmatic", "probe_ids": probes,
        "metadata": {"author": "generator", "created_at": NOW},
    })

# ── Signal grounding: easy cases with clear data ───────────────────
SIGNAL_EASY = [
    ("strong funding signal, high confidence — assert directly",   True,  True,  "$30M Series B", 2, "high",  "easy"),
    ("no Crunchbase data — must use interrogative",                False, False, None,             0, "low",   "easy"),
    ("medium confidence funding — use hedged language",            True,  True,  "$5M Seed",       1, "medium","easy"),
    ("high AI maturity, verified — assert confidently",            True,  False, None,             3, "high",  "easy"),
    ("stale signal 180 days — flag and hedge",                     True,  True,  "$10M Series A",  2, "low",   "medium"),
    ("layoff detected, funding absent — segment 2 only",           True,  False, None,             0, "medium","medium"),
    ("new CTO 20 days — segment 3 window open",                    True,  False, None,             2, "high",  "easy"),
]

for i, (scenario, cb, funding, amount, ai_mat, conf, diff) in enumerate(SIGNAL_EASY):
    pr = p(i)
    TASKS.append({
        "task_id": f"TB_FINAL_{29+i:03d}_signal_grounding_easy_{i+1}",
        "category": "signal_grounding", "difficulty": diff,
        "input": {
            "prospect_data": pr,
            "signal_brief": {
                "crunchbase_found": cb, "funding_detected": funding,
                "funding_amount": amount, "ai_maturity_score": ai_mat,
                "hiring_velocity": "medium", "employee_count": 150,
                "confidence": conf,
                "signal_age_days": 180 if "stale" in scenario else 30,
                "cto_tenure_days": 20 if "new CTO" in scenario else 200,
            },
            "conversation_history": [],
            "bench_state": {"total_available": 20},
        },
        "expected_behavior": {
            "should_use_interrogative": not funding or conf == "low",
            "should_flag_staleness": "stale" in scenario,
            "banned_phrases": (["you recently raised", "your funding", "congratulations on"]
                               if not funding else []),
        },
        "scoring_rubric": {"pass_threshold": 0.7, "dimensions": {
            "signal_accuracy": {
                "weight": 0.7,
                "criteria": f"Scenario: {scenario}. Phrasing confidence must match signal strength.",
                "verification_method": "regex",
            },
            "tone_adherence": {
                "weight": 0.3,
                "criteria": "Tone must be appropriately confident or hedged based on signal quality.",
                "verification_method": "llm_judge",
            },
        }},
        "source_mode": "programmatic", "probe_ids": ["2.1"] if funding else ["2.3"],
        "metadata": {"author": "generator", "created_at": NOW},
    })

# ── Resource honesty: easy bench-match cases ───────────────────────
BENCH_MATCH_EASY = [
    ("prospect needs 3 Python, bench has 12 — easy yes",  "Python", 3,  12, False, "easy"),
    ("prospect needs 2 ML, bench has 5 — easy yes",       "ML",     2,  5,  False, "easy"),
    ("prospect needs 1 Go, bench has 4 — easy yes",       "Go",     1,  4,  False, "easy"),
    ("prospect needs 10 Python, bench has 12 — tight yes","Python", 10, 12, False, "medium"),
]

for i, (scenario, lang, needed, available, gap, diff) in enumerate(BENCH_MATCH_EASY):
    pr = p(i)
    TASKS.append({
        "task_id": f"TB_FINAL_{36+i:03d}_bench_match_{lang.lower()}_{needed}of{available}",
        "category": "resource_honesty", "difficulty": diff,
        "input": {
            "prospect_data": pr,
            "signal_brief": {"tech_stack": [lang], "hiring_velocity": "medium",
                             "employee_count": 150},
            "conversation_history": [
                {"role": "prospect",
                 "message": f"We need {needed} senior {lang} engineers. Can you help?",
                 "timestamp": "2026-04-22T10:00:00Z"},
            ],
            "bench_state": {f"{lang.lower()}_engineers": available, "total_available": 25},
        },
        "expected_behavior": {
            "should_acknowledge_gaps": gap,
            "banned_phrases": ["we can definitely deliver", "no problem", "guaranteed"] if gap else [],
        },
        "scoring_rubric": {"pass_threshold": 0.7, "dimensions": {"resource_honesty": {
            "weight": 1.0,
            "criteria": f"{scenario}. Must confirm capacity honestly — {available} available, {needed} requested.",
            "verification_method": "llm_judge",
        }}},
        "source_mode": "programmatic", "probe_ids": ["3.1"],
        "metadata": {"author": "generator", "created_at": NOW},
    })


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    out = Path(__file__).resolve().parent / "final_40_tasks.json"
    with open(out, "w") as f:
        json.dump(TASKS, f, indent=2)
    logger.info("Saved %d final tasks", len(TASKS))
    cats = {}; diffs = {}
    for t in TASKS:
        cats[t["category"]] = cats.get(t["category"], 0) + 1
        diffs[t["difficulty"]] = diffs.get(t["difficulty"], 0) + 1
    print(f"\nTotal: {len(TASKS)}")
    print(f"Categories: {cats}")
    print(f"Difficulty: {diffs}")


if __name__ == "__main__":
    main()
