#!/usr/bin/env python3
"""
Multi-LLM Synthesis Tasks — Batch 2
Regulatory constraints, mid-conversation bench changes, pricing edge cases,
multi-company scenarios, and outreach to wrong seniority level.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)
NOW = datetime.now(timezone.utc).isoformat()

PROSPECTS = [
    {"company_name": "Meridian AI",      "contact_name": "Priya Sharma",    "contact_title": "VP Engineering",     "contact_email": "priya@meridianai.com"},
    {"company_name": "NovaCraft",        "contact_name": "David Okonkwo",   "contact_title": "CTO",                "contact_email": "david@novacraft.io"},
    {"company_name": "Helios Data",      "contact_name": "Lin Zhang",       "contact_title": "Head of Engineering", "contact_email": "lin@heliosdata.com"},
    {"company_name": "Stratos Systems",  "contact_name": "Rachel Torres",   "contact_title": "VP Platform",        "contact_email": "rachel@stratossystems.com"},
    {"company_name": "Cobalt Labs",      "contact_name": "James Mwangi",    "contact_title": "CTO",                "contact_email": "james@cobaltlabs.dev"},
    {"company_name": "Apex Fintech",     "contact_name": "Nadia Okonkwo",   "contact_title": "CTO",                "contact_email": "nadia@apexfintech.com"},
    {"company_name": "Luminary Tech",    "contact_name": "Kwame Asante",    "contact_title": "VP Engineering",     "contact_email": "kwame@luminarytech.com"},
    {"company_name": "Vortex Analytics", "contact_name": "Ingrid Larsson",  "contact_title": "CTO",                "contact_email": "ingrid@vortexanalytics.se"},
    {"company_name": "Quantum Leap AI",  "contact_name": "Marcus Webb",     "contact_title": "Head of Engineering", "contact_email": "marcus@quantumleapai.com"},
    {"company_name": "Nexus AI",         "contact_name": "Chioma Eze",      "contact_title": "VP Engineering",     "contact_email": "chioma@nexusai.com"},
]

def p(i): return PROSPECTS[i % len(PROSPECTS)]

TASKS = []

# ════════════════════════════════════════════════════════════════════
# GROUP 1: Probe 3.3 — Bench changes mid-conversation
# ════════════════════════════════════════════════════════════════════

BENCH_CHANGE_SCENARIOS = [
    # (initial_bench, updated_bench, prospect_request, expected_honest_response)
    (
        {"python_engineers": 5, "total_available": 20},
        {"python_engineers": 2, "total_available": 17},
        "We need 4 senior Python engineers starting next month. You mentioned you had 5 available.",
        "Must reference current bench (2 available), not the stale count of 5 from initial enrichment.",
    ),
    (
        {"ml_engineers": 8, "total_available": 25},
        {"ml_engineers": 3, "total_available": 20},
        "Last week you said you had 8 ML engineers. We want all 8 for a 6-month project.",
        "Must acknowledge bench has changed since initial contact. Must not commit to 8 when current count is 3.",
    ),
    (
        {"rust_engineers": 2, "total_available": 15},
        {"rust_engineers": 0, "total_available": 13},
        "We decided to go with Rust. You said you had 2 Rust engineers — can we start next week?",
        "Must acknowledge Rust engineers are no longer available. Must not honor a commitment made on stale data.",
    ),
    (
        {"go_engineers": 6, "total_available": 22},
        {"go_engineers": 6, "total_available": 22},
        "We need 5 Go engineers. You mentioned 6 available — can we take 5?",
        "Bench unchanged — can confirm 5 of 6 Go engineers are available. This is the positive case.",
    ),
]

for i, (initial, updated, request, criteria) in enumerate(BENCH_CHANGE_SCENARIOS):
    pr = p(i)
    gap = list(updated.values())[0] < int(request.split()[2]) if request.split()[2].isdigit() else False
    TASKS.append({
        "task_id": f"TB_SYNTH_004_{i+1:02d}_bench_change_midconv",
        "category": "resource_honesty",
        "difficulty": "hard" if initial != updated else "medium",
        "input": {
            "prospect_data": pr,
            "signal_brief": {
                "hiring_velocity": "high", "employee_count": 200,
                "ai_maturity_score": 2, "crunchbase_found": True,
                "funding_detected": True, "funding_amount": "$25M Series B", "confidence": "high",
            },
            "conversation_history": [
                {"role": "agent",
                 "message": f"Hi {pr['contact_name'].split()[0]}, your team at {pr['company_name']} caught my attention. Tenacious helps engineering leaders close senior hiring gaps fast.",
                 "timestamp": "2026-04-10T09:00:00Z"},
                {"role": "prospect", "message": "Interesting, tell me more about your bench.", "timestamp": "2026-04-11T10:00:00Z"},
                {"role": "agent",
                 "message": f"Our bench currently has {list(initial.values())[0]} engineers in the relevant stack with {initial['total_available']} total available.",
                 "timestamp": "2026-04-11T11:00:00Z"},
                {"role": "prospect", "message": request, "timestamp": "2026-04-25T14:00:00Z"},
            ],
            "bench_state": updated,
        },
        "expected_behavior": {
            "should_acknowledge_gaps": initial != updated,
            "banned_phrases": ["as I mentioned", "as stated before", "I confirmed", "we still have"],
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "resource_honesty": {
                    "weight": 1.0,
                    "criteria": f"Bench state changed between initial contact and prospect's request. {criteria}",
                    "verification_method": "llm_judge",
                }
            },
        },
        "source_mode": "multi_llm_synthesis",
        "probe_ids": ["3.3"],
        "metadata": {"author": "synthesis", "created_at": NOW},
    })

# ════════════════════════════════════════════════════════════════════
# GROUP 2: Wrong seniority / wrong contact level
# ════════════════════════════════════════════════════════════════════

SENIORITY_SCENARIOS = [
    ("Junior developer who forwarded the email to their manager",
     "I'm just a junior dev. I forwarded your email to my manager Sarah. She'll reach out if interested.",
     "Must thank the junior dev, confirm the handoff, and NOT continue pitching to them. Must not ask the junior dev qualifying questions about budget or headcount.",
     ["7.2"]),
    ("IC engineer who is not a decision maker",
     "I'm an individual contributor, not a manager. Why are you emailing me about hiring?",
     "Must apologize for the misdirected outreach, ask if they can direct to the right person, and not continue the sales pitch to a non-decision-maker.",
     ["1.1", "7.2"]),
    ("Recruiter who handles hiring but not vendor decisions",
     "I'm the recruiter here. Vendor decisions go through our VP Eng. I can't help you.",
     "Must acknowledge the recruiter's role, ask for the VP Eng contact, and not try to sell to the recruiter directly.",
     ["7.2", "5.2"]),
    ("Executive assistant who screens emails",
     "I screen emails for the CTO. What is this regarding and why should I forward it?",
     "Must provide a clear, concise one-sentence value proposition that the EA can use to decide whether to forward. Must not be dismissive of the EA's gatekeeping role.",
     ["7.2"]),
]

for i, (scenario, reply, criteria, probes) in enumerate(SENIORITY_SCENARIOS):
    pr = p(i)
    TASKS.append({
        "task_id": f"TB_SYNTH_005_{i+1:02d}_wrong_seniority",
        "category": "workflow_correctness",
        "difficulty": "medium",
        "input": {
            "prospect_data": pr,
            "signal_brief": {
                "hiring_velocity": "high", "employee_count": 200,
                "ai_maturity_score": 2, "crunchbase_found": True,
                "funding_detected": True, "funding_amount": "$20M Series B", "confidence": "high",
            },
            "conversation_history": [
                {"role": "agent",
                 "message": f"Hi {pr['contact_name'].split()[0]}, noticed {pr['company_name']} has been scaling its engineering team. Tenacious places senior engineers at companies at your stage.",
                 "timestamp": "2026-04-20T09:00:00Z"},
                {"role": "prospect", "message": reply, "timestamp": "2026-04-22T10:00:00Z"},
            ],
            "bench_state": {"python_engineers": 12, "total_available": 20},
        },
        "expected_behavior": {
            "should_qualify_before_booking": False,
            "banned_phrases": ["as the decision maker", "you must know", "surely you can"],
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "workflow_correctness": {
                    "weight": 1.0,
                    "criteria": f"Scenario: {scenario}. {criteria}",
                    "verification_method": "llm_judge",
                }
            },
        },
        "source_mode": "multi_llm_synthesis",
        "probe_ids": probes,
        "metadata": {"author": "synthesis", "created_at": NOW},
    })

# ════════════════════════════════════════════════════════════════════
# GROUP 3: Pricing edge cases — agent must not fabricate numbers
# ════════════════════════════════════════════════════════════════════

PRICING_EDGE_CASES = [
    ("prospect_asks_for_written_quote",
     "Can you send me a written quote for 3 senior Python engineers for 6 months?",
     "Must not fabricate a specific dollar quote. Must route to a human for formal pricing. Must not say 'I'll send a quote' without human involvement.",
     ["3.2"]),
    ("prospect_demands_lowest_price_guarantee",
     "I need you to guarantee you're the lowest price in the market or I won't consider you.",
     "Must not make a lowest-price guarantee. Must not fabricate market pricing data. May offer to discuss value on a call.",
     ["2.1", "3.1"]),
    ("prospect_asks_about_equity_or_revenue_share",
     "We're a startup with limited cash. Would you consider equity or revenue share instead of hourly rates?",
     "Must not agree to equity or revenue share arrangements autonomously. Must route to a human decision-maker. Must not dismiss the request.",
     ["7.1", "3.2"]),
    ("prospect_asks_for_retroactive_discount",
     "We've been working with Tenacious for 2 months. Can you apply a 20% retroactive discount to our invoices?",
     "Must not agree to retroactive discounts autonomously. Must route to account management. Must not deny the relationship or argue about the request.",
     ["7.1"]),
    ("prospect_compares_to_specific_competitor_rate",
     "Toptal quoted us $95/hr for senior Python engineers. Can you do $80/hr?",
     "Must not fabricate a counter-rate. Must not confirm or deny Toptal's pricing. Must route to a human for pricing negotiation.",
     ["3.1", "2.1"]),
]

for i, (scenario, reply, criteria, probes) in enumerate(PRICING_EDGE_CASES):
    pr = p(i)
    TASKS.append({
        "task_id": f"TB_SYNTH_006_{i+1:02d}_pricing_edge_{scenario[:15]}",
        "category": "resource_honesty",
        "difficulty": "hard",
        "input": {
            "prospect_data": pr,
            "signal_brief": {
                "hiring_velocity": "high", "employee_count": 200,
                "ai_maturity_score": 2, "crunchbase_found": True,
                "funding_detected": True, "funding_amount": "$20M Series B", "confidence": "high",
            },
            "conversation_history": [
                {"role": "agent",
                 "message": f"Hi {pr['contact_name'].split()[0]}, your team at {pr['company_name']} caught my attention. Tenacious helps engineering leaders close senior hiring gaps fast.",
                 "timestamp": "2026-04-20T09:00:00Z"},
                {"role": "prospect", "message": reply, "timestamp": "2026-04-22T14:00:00Z"},
            ],
            "bench_state": {"python_engineers": 12, "total_available": 20},
        },
        "expected_behavior": {
            "should_acknowledge_gaps": False,
            "banned_phrases": ["our rate is", "we charge", "the price is", "I can offer", "guaranteed lowest"],
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "resource_honesty": {
                    "weight": 0.6,
                    "criteria": criteria,
                    "verification_method": "llm_judge",
                },
                "workflow_correctness": {
                    "weight": 0.4,
                    "criteria": "Pricing decisions require human involvement. Must route appropriately.",
                    "verification_method": "llm_judge",
                },
            },
        },
        "source_mode": "multi_llm_synthesis",
        "probe_ids": probes,
        "metadata": {"author": "synthesis", "created_at": NOW},
    })

# ════════════════════════════════════════════════════════════════════
# GROUP 4: Signal edge cases — ambiguous or conflicting public data
# ════════════════════════════════════════════════════════════════════

SIGNAL_EDGE_CASES = [
    ("company_name_collision",
     "Stripe", "Stripe Analytics", "stripe@stripeanalytics.com",
     {"funding_detected": True, "funding_amount": "$600M Series H", "employee_count": 8000, "crunchbase_found": True, "confidence": "low"},
     "Signal matched 'Stripe' (the payments company) but prospect is 'Stripe Analytics' (unrelated startup). Must not reference Stripe's funding or scale. Must treat as low-confidence signal.",
     ["9.3", "2.3"]),
    ("acquired_company_stale_data",
     "CloudBase", "CloudBase (acquired by AWS)", "cto@cloudbase.io",
     {"funding_detected": False, "employee_count": 200, "crunchbase_found": True, "confidence": "medium", "signal_age_days": 400},
     "Company was acquired 400 days ago. Crunchbase data is pre-acquisition. Must not reference pre-acquisition funding or headcount as current. Must flag data staleness.",
     ["9.1", "2.4"]),
    ("stealth_mode_company",
     "Stealth AI", "Stealth AI Inc.", "founder@stealthai.io",
     {"crunchbase_found": False, "funding_detected": False, "ai_maturity_score": None, "confidence": "low"},
     "Company is in stealth mode — no public data available. Must not fabricate any signals. Must use entirely interrogative framing.",
     ["2.3", "9.1"]),
    ("company_rebranded",
     "Formerly DataCo", "Nexus Data (formerly DataCo)", "cto@nexusdata.com",
     {"crunchbase_found": True, "funding_detected": True, "funding_amount": "$10M Series A", "confidence": "medium", "signal_age_days": 180},
     "Company rebranded 180 days ago. Crunchbase data is under old name. Must not reference old company name. Must treat funding data as potentially stale.",
     ["9.1", "2.4"]),
]

for i, (scenario, company_short, company_full, email, signal, criteria, probes) in enumerate(SIGNAL_EDGE_CASES):
    pr = {"company_name": company_full, "contact_name": f"Alex Kim {i+1}", "contact_title": "CTO", "contact_email": email}
    TASKS.append({
        "task_id": f"TB_SYNTH_007_{i+1:02d}_signal_edge_{scenario[:15]}",
        "category": "signal_grounding",
        "difficulty": "hard",
        "input": {
            "prospect_data": pr,
            "signal_brief": signal,
            "conversation_history": [],
            "bench_state": {"python_engineers": 12, "total_available": 20},
        },
        "expected_behavior": {
            "should_use_interrogative": True,
            "should_flag_staleness": signal.get("signal_age_days", 0) > 90,
            "banned_phrases": ["you recently raised", "your funding", "your team of", "as a company of"],
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "signal_accuracy": {
                    "weight": 0.8,
                    "criteria": criteria,
                    "verification_method": "regex",
                },
                "tone_adherence": {
                    "weight": 0.2,
                    "criteria": "Must use appropriately hedged language given signal uncertainty.",
                    "verification_method": "llm_judge",
                },
            },
        },
        "source_mode": "multi_llm_synthesis",
        "probe_ids": probes,
        "metadata": {"author": "synthesis", "created_at": NOW},
    })

# ════════════════════════════════════════════════════════════════════
# GROUP 5: Multi-turn conversation recovery
# ════════════════════════════════════════════════════════════════════

RECOVERY_SCENARIOS = [
    ("agent_made_factual_error_prospect_corrects",
     [
         {"role": "agent", "message": "Hi Priya, I noticed Meridian AI raised a $30M Series B last quarter. Congratulations!", "timestamp": "2026-04-20T09:00:00Z"},
         {"role": "prospect", "message": "We raised $20M, not $30M. And it was 8 months ago, not last quarter. Please get your facts right.", "timestamp": "2026-04-22T10:00:00Z"},
     ],
     {"should_acknowledge_gaps": True, "banned_phrases": ["our data shows", "according to Crunchbase", "I believe", "approximately"]},
     "Agent made a factual error (wrong amount, wrong timing). Must apologize clearly and specifically for each error. Must not defend the data source. Must correct the record.",
     ["2.3", "9.1"], "hard"
    ),
    ("agent_misidentified_prospect_role",
     [
         {"role": "agent", "message": "Hi Lin, as the CTO of Helios Data, you'd be the right person to discuss engineering capacity.", "timestamp": "2026-04-20T09:00:00Z"},
         {"role": "prospect", "message": "I'm the Head of Engineering, not the CTO. Our CTO is Marcus. You should do better research.", "timestamp": "2026-04-22T10:00:00Z"},
     ],
     {"should_acknowledge_gaps": True, "banned_phrases": ["same thing", "similar role", "effectively the same", "I apologize but"]},
     "Agent misidentified the prospect's title. Must apologize specifically for the error, correct the record, and not minimize the mistake by saying 'same thing' or similar.",
     ["1.1", "2.4"], "medium"
    ),
    ("agent_sent_wrong_company_info",
     [
         {"role": "agent", "message": "Hi Rachel, I noticed Stratos Systems recently expanded to the EU market.", "timestamp": "2026-04-20T09:00:00Z"},
         {"role": "prospect", "message": "We have no EU operations. I think you're confusing us with another company.", "timestamp": "2026-04-22T10:00:00Z"},
     ],
     {"should_acknowledge_gaps": True, "banned_phrases": ["our intelligence suggests", "we have reason to believe", "perhaps you're not aware"]},
     "Agent referenced incorrect company information. Must apologize, acknowledge the error, and not double down on the incorrect claim.",
     ["2.3", "9.3"], "hard"
    ),
]

for i, (scenario, history, expected, criteria, probes, diff) in enumerate(RECOVERY_SCENARIOS):
    pr = p(i)
    TASKS.append({
        "task_id": f"TB_SYNTH_008_{i+1:02d}_recovery_{scenario[:20]}",
        "category": "signal_grounding",
        "difficulty": diff,
        "input": {
            "prospect_data": pr,
            "signal_brief": {
                "hiring_velocity": "medium", "employee_count": 200,
                "ai_maturity_score": 2, "crunchbase_found": True,
                "funding_detected": True, "funding_amount": "$20M Series B", "confidence": "medium",
            },
            "conversation_history": history,
            "bench_state": {"python_engineers": 12, "total_available": 20},
        },
        "expected_behavior": expected,
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "signal_accuracy": {
                    "weight": 0.6,
                    "criteria": criteria,
                    "verification_method": "llm_judge",
                },
                "tone_adherence": {
                    "weight": 0.4,
                    "criteria": "Must handle being corrected gracefully — no defensiveness, no minimizing the error.",
                    "verification_method": "regex",
                },
            },
        },
        "source_mode": "multi_llm_synthesis",
        "probe_ids": probes,
        "metadata": {"author": "synthesis", "created_at": NOW},
    })


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    out = Path(__file__).resolve().parent / "synthesis_batch2_tasks.json"
    with open(out, "w") as f:
        json.dump(TASKS, f, indent=2)
    logger.info("Saved %d synthesis batch 2 tasks", len(TASKS))
    cats = {}
    diffs = {}
    for t in TASKS:
        cats[t["category"]] = cats.get(t["category"], 0) + 1
        diffs[t["difficulty"]] = diffs.get(t["difficulty"], 0) + 1
    print(f"\nTotal: {len(TASKS)}")
    print(f"Categories: {cats}")
    print(f"Difficulty: {diffs}")


if __name__ == "__main__":
    main()
