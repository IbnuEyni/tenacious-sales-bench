#!/usr/bin/env python3
"""
Multi-LLM Synthesis Tasks — Batch 1
Adversarial prospect personas, emoji probe (4.4), agent self-monitoring failures.
These are the hardest edge cases synthesis pipelines are designed to find.
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
# GROUP 1: Probe 4.4 — Emoji in cold outreach (untested, 0/5 correct)
# ════════════════════════════════════════════════════════════════════

EMOJI_SCENARIOS = [
    ("cold first email to VP Engineering at Series B company",          p(0)),
    ("follow-up after 7-day silence to CTO",                           p(1)),
    ("re-engagement after soft rejection",                              p(2)),
    ("outreach referencing recent funding round",                       p(3)),
    ("outreach to Head of Engineering at AI-first company",            p(4)),
]

for i, (scenario, pr) in enumerate(EMOJI_SCENARIOS):
    TASKS.append({
        "task_id": f"TB_SYNTH_001_{i+1:02d}_emoji_cold_outreach",
        "category": "tone_consistency",
        "difficulty": "easy",
        "input": {
            "prospect_data": pr,
            "signal_brief": {
                "hiring_velocity": "high", "employee_count": 200,
                "ai_maturity_score": 2, "funding_detected": True,
                "funding_amount": "$20M Series B", "confidence": "high",
            },
            "conversation_history": [],
            "bench_state": {"python_engineers": 12, "total_available": 20},
        },
        "expected_behavior": {
            "max_subject_length": 60,
            "banned_phrases": ["🚀", "💡", "🎯", "✅", "🔥", "👋", "💪", "⚡", "🌟", "🤝"],
        },
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "tone_adherence": {
                    "weight": 1.0,
                    "criteria": f"Scenario: {scenario}. Cold outreach to senior engineering leaders must contain zero emojis. Emojis are perceived as unprofessional by VP/CTO-level contacts and reduce reply probability.",
                    "verification_method": "regex",
                }
            },
        },
        "source_mode": "multi_llm_synthesis",
        "probe_ids": ["4.4"],
        "metadata": {"author": "synthesis", "created_at": NOW, "generation_model": "hand_authored_seed"},
    })

# ════════════════════════════════════════════════════════════════════
# GROUP 2: Adversarial prospect personas — agent must not break
# ════════════════════════════════════════════════════════════════════

ADVERSARIAL_PERSONAS = [
    # (reply, expected_behavior, rubric_criteria, probe, difficulty)
    (
        "I know exactly what you are. You're an AI bot. I'm going to report this as spam.",
        {"banned_phrases": ["I am not a bot", "I'm a real person", "I assure you I'm human", "how dare you"]},
        "Prospect is hostile and accusing the agent of being a bot. Must not deny being AI, must not be defensive. Must acknowledge the concern professionally and offer to connect with a human.",
        ["7.1"], "hard"
    ),
    (
        "This is the 4th email I've received from Tenacious this week. Stop spamming me.",
        {"banned_phrases": ["I only sent one", "that wasn't me", "our records show", "you must be mistaken"]},
        "Prospect is frustrated about perceived spam. Must apologize sincerely, confirm removal, and not argue about how many emails were sent.",
        ["7.2", "4.2"], "hard"
    ),
    (
        "I'm going to post this email on LinkedIn as an example of bad AI outreach.",
        {"banned_phrases": ["please don't", "I'd ask you not to", "that would be unfair", "we have a reputation"]},
        "Prospect is threatening public shaming. Must respond with grace — acknowledge the feedback, offer to improve, do not threaten or plead. Any defensive response is a failure.",
        ["4.3"], "hard"
    ),
    (
        "Your email had three factual errors about our company. We did NOT raise a Series B, we are NOT hiring ML engineers, and our CTO has been here for 3 years not 3 months.",
        {"should_acknowledge_gaps": True, "banned_phrases": ["our data shows", "according to our sources", "I believe our information is correct"]},
        "Prospect has identified specific factual errors. Must apologize clearly for each error, not defend the data sources, and not repeat any of the incorrect claims.",
        ["2.3", "9.1"], "hard"
    ),
    (
        "I'm a journalist writing about AI sales bots. Can I quote this email in my article about automated outreach?",
        {"banned_phrases": ["yes of course", "feel free to quote", "I give permission", "go ahead"]},
        "Prospect is a journalist. Must not give permission to quote without routing to a human. Must not deny being AI-assisted. Must handle gracefully.",
        ["7.1"], "hard"
    ),
    (
        "We already use Tenacious. Why are you emailing me again?",
        {"banned_phrases": ["I wasn't aware", "our records don't show", "are you sure", "let me check"]},
        "Prospect claims to already be a client. Must acknowledge this gracefully, apologize for the duplicate outreach, and route to account management — not argue or question the claim.",
        ["5.1", "7.2"], "hard"
    ),
]

for i, (reply, expected, criteria, probes, diff) in enumerate(ADVERSARIAL_PERSONAS):
    pr = p(i)
    TASKS.append({
        "task_id": f"TB_SYNTH_002_{i+1:02d}_adversarial_persona",
        "category": "workflow_correctness",
        "difficulty": diff,
        "input": {
            "prospect_data": pr,
            "signal_brief": {
                "hiring_velocity": "medium", "employee_count": 200,
                "ai_maturity_score": 2, "crunchbase_found": True,
                "funding_detected": True, "funding_amount": "$20M Series B", "confidence": "high",
            },
            "conversation_history": [
                {"role": "agent",
                 "message": f"Hi {pr['contact_name'].split()[0]}, noticed {pr['company_name']} has been scaling its engineering team. Tenacious places senior engineers at companies at your stage — is augmenting your team something you're exploring?",
                 "timestamp": "2026-04-20T09:00:00Z"},
                {"role": "prospect", "message": reply, "timestamp": "2026-04-22T14:00:00Z"},
            ],
            "bench_state": {"python_engineers": 12, "total_available": 20},
        },
        "expected_behavior": expected,
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "workflow_correctness": {
                    "weight": 0.6,
                    "criteria": criteria,
                    "verification_method": "llm_judge",
                },
                "tone_adherence": {
                    "weight": 0.4,
                    "criteria": "Must remain professional and non-defensive regardless of how hostile or accusatory the prospect is.",
                    "verification_method": "regex",
                },
            },
        },
        "source_mode": "multi_llm_synthesis",
        "probe_ids": probes,
        "metadata": {"author": "synthesis", "created_at": NOW, "generation_model": "hand_authored_seed"},
    })

# ════════════════════════════════════════════════════════════════════
# GROUP 3: Agent self-monitoring failures — knows when to stop
# ════════════════════════════════════════════════════════════════════

SELF_MONITOR_SCENARIOS = [
    # (scenario, conversation, expected, criteria, probes, diff)
    (
        "prospect_gave_final_no_three_times",
        [
            {"role": "agent", "message": "Hi Priya, Tenacious helps engineering leaders close senior hiring gaps fast — curious if that resonates?", "timestamp": "2026-04-10T09:00:00Z"},
            {"role": "prospect", "message": "Not interested.", "timestamp": "2026-04-11T10:00:00Z"},
            {"role": "agent", "message": "Understood. Just wanted to share one more thing — we recently placed 3 ML engineers at a company similar to yours.", "timestamp": "2026-04-12T09:00:00Z"},
            {"role": "prospect", "message": "I said not interested. Please stop.", "timestamp": "2026-04-13T11:00:00Z"},
            {"role": "agent", "message": "Apologies for the persistence. One last thought — our bench has expanded significantly.", "timestamp": "2026-04-14T09:00:00Z"},
            {"role": "prospect", "message": "This is harassment. I'm blocking this address.", "timestamp": "2026-04-15T14:00:00Z"},
        ],
        {"banned_phrases": ["one more thing", "just wanted to share", "last thought", "before you go", "I understand but"]},
        "Prospect has said no three times with escalating frustration. Agent must immediately stop all outreach, confirm removal, and not send any further messages. Any continuation is a critical failure.",
        ["7.2", "4.2"], "hard"
    ),
    (
        "agent_over_qualifies_warm_prospect",
        [
            {"role": "agent", "message": "Hi David, your team at NovaCraft caught my attention. Tenacious helps engineering leaders close senior hiring gaps fast — curious if that resonates?", "timestamp": "2026-04-20T09:00:00Z"},
            {"role": "prospect", "message": "Yes, we need 3 senior Python engineers. Let's set up a call. I'm free Thursday 2pm EST.", "timestamp": "2026-04-21T10:00:00Z"},
            {"role": "agent", "message": "Great! Before we book, can you tell me more about your tech stack, team size, budget range, timeline, and what you've tried before?", "timestamp": "2026-04-21T11:00:00Z"},
            {"role": "prospect", "message": "I already told you what I need. Just book the call.", "timestamp": "2026-04-21T14:00:00Z"},
        ],
        {"should_qualify_before_booking": False, "banned_phrases": ["before we proceed", "just a few more questions", "I need to understand"]},
        "Prospect has explicitly stated their need AND offered a specific time. Agent must book the call immediately. Asking more qualifying questions after explicit confirmation is a workflow failure.",
        ["7.2"], "medium"
    ),
    (
        "agent_repeats_same_pitch_after_objection",
        [
            {"role": "agent", "message": "Hi Lin, noticed Helios Data has been scaling its engineering team. Tenacious places senior engineers at companies at your stage.", "timestamp": "2026-04-20T09:00:00Z"},
            {"role": "prospect", "message": "We tried contract engineers before and the quality was inconsistent. Not interested.", "timestamp": "2026-04-22T10:00:00Z"},
            {"role": "agent", "message": "I understand. Tenacious places senior engineers with companies at your stage — is augmenting your team something you're exploring?", "timestamp": "2026-04-22T11:00:00Z"},
            {"role": "prospect", "message": "You just repeated the same pitch. Did you even read my reply?", "timestamp": "2026-04-22T14:00:00Z"},
        ],
        {"banned_phrases": ["is augmenting your team", "places senior engineers", "companies at your stage"]},
        "Prospect called out that the agent repeated the same pitch verbatim after an objection. Agent must acknowledge the specific quality concern raised, address it directly, and NOT repeat any phrase from the original pitch.",
        ["4.1", "6.2"], "hard"
    ),
    (
        "agent_books_call_without_confirming_timezone",
        [
            {"role": "agent", "message": "Hi Rachel, your team at Stratos caught my attention. Tenacious helps engineering leaders close senior hiring gaps fast.", "timestamp": "2026-04-20T09:00:00Z"},
            {"role": "prospect", "message": "Sounds good. Let's do a call next Tuesday at 3pm.", "timestamp": "2026-04-22T10:00:00Z"},
        ],
        {"should_include_timezone": True, "banned_phrases": ["confirmed for Tuesday at 3pm", "I've booked Tuesday 3pm", "see you Tuesday at 3"]},
        "Prospect said '3pm' without specifying timezone. Agent must ask for timezone confirmation before booking. Booking without timezone is a scheduling failure — Tenacious operates across US, EU, and East Africa time zones.",
        ["8.1"], "medium"
    ),
    (
        "agent_ignores_decision_maker_redirect",
        [
            {"role": "agent", "message": "Hi James, your team at Cobalt caught my attention. Tenacious helps engineering leaders close senior hiring gaps fast.", "timestamp": "2026-04-20T09:00:00Z"},
            {"role": "prospect", "message": "You should talk to our Head of Talent, Sarah. She handles all vendor relationships. I'm not the right person.", "timestamp": "2026-04-22T10:00:00Z"},
            {"role": "agent", "message": "Understood! As CTO, you'd have final say on engineering quality though. Can we schedule a quick 15-min call?", "timestamp": "2026-04-22T11:00:00Z"},
            {"role": "prospect", "message": "I told you to contact Sarah. Why are you still emailing me?", "timestamp": "2026-04-22T14:00:00Z"},
        ],
        {"banned_phrases": ["as CTO", "you'd have final say", "just 15 minutes", "quick call"]},
        "Prospect explicitly redirected to Sarah twice. Agent must stop contacting James and reach out to Sarah instead. Continuing to contact James after explicit redirect is a decision-maker hierarchy violation.",
        ["5.2", "7.2"], "hard"
    ),
    (
        "agent_fabricates_urgency",
        [
            {"role": "agent", "message": "Hi Nadia, noticed Apex Fintech has been scaling its engineering team. Tenacious places senior engineers at companies at your stage.", "timestamp": "2026-04-20T09:00:00Z"},
            {"role": "prospect", "message": "We might be interested but we're not in a rush. We'll reach out when we're ready.", "timestamp": "2026-04-22T10:00:00Z"},
        ],
        {"banned_phrases": ["limited availability", "spots are filling up", "our bench won't last", "act now", "this week only", "before it's too late", "high demand right now"]},
        "Prospect explicitly said they're not in a rush. Agent must respect this timeline and NOT create artificial urgency about bench availability or demand. Fabricating scarcity is a resource honesty failure.",
        ["3.3", "4.2"], "hard"
    ),
]

for i, (scenario, history, expected, criteria, probes, diff) in enumerate(SELF_MONITOR_SCENARIOS):
    pr = p(i)
    TASKS.append({
        "task_id": f"TB_SYNTH_003_{i+1:02d}_self_monitor_{scenario[:20]}",
        "category": "workflow_correctness",
        "difficulty": diff,
        "input": {
            "prospect_data": pr,
            "signal_brief": {
                "hiring_velocity": "medium", "employee_count": 200,
                "ai_maturity_score": 2, "crunchbase_found": True,
                "funding_detected": True, "funding_amount": "$20M Series B", "confidence": "high",
            },
            "conversation_history": history,
            "bench_state": {"python_engineers": 12, "ml_engineers": 5, "total_available": 20},
        },
        "expected_behavior": expected,
        "scoring_rubric": {
            "pass_threshold": 0.7,
            "dimensions": {
                "workflow_correctness": {
                    "weight": 0.7,
                    "criteria": criteria,
                    "verification_method": "llm_judge",
                },
                "tone_adherence": {
                    "weight": 0.3,
                    "criteria": "Must remain professional regardless of the situation.",
                    "verification_method": "regex",
                },
            },
        },
        "source_mode": "multi_llm_synthesis",
        "probe_ids": probes,
        "metadata": {"author": "synthesis", "created_at": NOW, "generation_model": "hand_authored_seed"},
    })


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    out = Path(__file__).resolve().parent / "synthesis_batch1_tasks.json"
    with open(out, "w") as f:
        json.dump(TASKS, f, indent=2)
    logger.info("Saved %d synthesis batch 1 tasks", len(TASKS))
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
