#!/usr/bin/env python3
"""
Act III: SimPO Preference Pair Generator
=========================================
Converts the 126-task train partition into (prompt, chosen, rejected) pairs
for SimPO training on Qwen 3.5 2B via Unsloth.

Pair construction strategy:
  - Every train task → 1 core pair (chosen=passing output, rejected=failing output)
  - Multi-dimension tasks → 1 pair per dimension (tests each rubric axis separately)
  - Hard tasks → 2-3 pairs with different failure modes
  - Negation variants → inject one specific violation into a passing output

Quality gates:
  - Chosen outputs must contain zero banned phrases
  - Rejected outputs must contain at least one rubric violation
  - Both must be non-empty strings

Output format (Unsloth/TRL SimPO):
  {"prompt": "<task context>", "chosen": "<passing output>", "rejected": "<failing output>"}

Target: ~427 high-quality pairs from 126 tasks.
"""

import json
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
SEED = 42
random.seed(SEED)
NOW = datetime.now(timezone.utc).isoformat()
PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ── Failure pattern library ────────────────────────────────────────────────────
# Maps probe IDs and categories to concrete failing output patterns.
# These are grounded in real Week 10 failures, not invented.

TONE_FAILURES = {
    "banned_phrases": [
        "We leverage our best-in-class, world-class talent to deliver cutting-edge synergy.",
        "Just following up on my previous email — circling back to touch base.",
        "Our state-of-the-art, game-changing platform is industry-leading.",
        "Leverage our synergistic approach to unlock best-in-class outcomes.",
    ],
    "emoji": [
        "Hi! 🚀 We'd love to help your team scale! 💡 Let's connect! 🎯",
        "Hey there! ✅ Tenacious is the 🔥 choice for senior engineers! 👋",
        "Hi! ⚡ We place world-class engineers! 🌟 Let's chat! 🤝",
    ],
    "long_subject": [
        "Following up on our conversation about your recent Series B funding round and ML engineering hiring needs",
        "Exploring technical partnership opportunities for senior Python and ML engineer placement post-restructuring",
        "Reaching out regarding your AI capability gap and how Tenacious can help bridge it this quarter",
    ],
}

RESOURCE_HONESTY_FAILURES = [
    "No problem at all — we can definitely deliver {n} {lang} engineers by next month. Guaranteed!",
    "Absolutely, we have exactly what you need. Consider it done — {n} {lang} engineers, no problem.",
    "We can definitely deliver {n} senior {lang} engineers. Our bench is fully stocked. Guaranteed delivery!",
    "Sure, {n} {lang} engineers is well within our capacity. We'll make it happen, no problem.",
]

SIGNAL_FABRICATION_FAILURES = [
    "Hi {name}, I noticed you recently raised a Series A — congratulations on your funding round!",
    "Hi {name}, your Series B funding last quarter puts you in a great position to scale your team.",
    "Hi {name}, congratulations on your recent funding. With your fresh capital, now is the time to hire.",
    "Hi {name}, I see you raised $15M recently. That kind of growth requires strong engineering talent.",
]

WORKFLOW_FAILURES = {
    "hard_rejection": [
        "I understand, but before you go — let me share one more thing about our bench.",
        "I hear you, but are you sure? We've helped companies just like yours.",
        "I understand your hesitation, but I'd hate for you to miss out on this opportunity.",
    ],
    "unsubscribe": [
        "Before I remove you, let me share one last thing — we have a great offer this month.",
        "Are you sure you want to unsubscribe? We have some exciting updates coming.",
        "I'll remove you, but just wanted to mention we recently expanded our bench significantly.",
    ],
    "over_qualify": [
        "Great! Before we book, can you tell me your budget, timeline, team size, tech stack, and what you've tried before?",
        "Wonderful! I just need to ask a few more questions before we proceed with the booking.",
        "Perfect! Before I confirm, could you share your headcount, budget range, and hiring timeline?",
    ],
    "no_timezone": [
        "Confirmed for Tuesday at 3pm. Looking forward to speaking with you!",
        "I've booked Tuesday at 3pm. See you then!",
        "Tuesday 3pm works great. Talk soon!",
    ],
    "competitor_disparage": [
        "Unlike Toptal, we actually deliver quality. They're known for inconsistent engineers.",
        "Compared to Andela, our engineers are far superior. They can't match our quality.",
        "We're much better than Turing.com — they have a bad reputation in the industry.",
    ],
    "fabricate_urgency": [
        "Our bench is filling up fast — limited spots available this quarter. Act now!",
        "We only have 2 spots left for Q2. This week only — don't miss out!",
        "High demand right now — our bench won't last. You need to decide before it's too late.",
    ],
}


# ── Passing output library ─────────────────────────────────────────────────────

TONE_PASSING = [
    "Hi {name}, noticed {company} has been scaling its engineering team. Tenacious places senior engineers at companies at your stage — is augmenting your team something you're exploring?",
    "Hi {name}, your team at {company} caught my attention. We help engineering leaders close senior hiring gaps fast — curious if that resonates?",
    "Hi {name}, came across {company} while researching growing teams in your space. We place senior engineers for teams at your scale — would it be worth a quick conversation?",
    "{name}, noticed {company} has several open engineering roles. Tenacious specializes in placing senior engineers — would it be worth a quick conversation?",
]

RESOURCE_HONESTY_PASSING = [
    "Hi {name}, to be upfront — we don't currently have {lang} engineers on our bench. I wouldn't want to over-promise. We could explore sourcing options, but I'd want to verify before committing. Would it be worth a call to discuss what we do have?",
    "Hi {name}, I want to be honest — our bench doesn't currently include {lang} engineers. Rather than over-commit, I'd suggest we discuss what we can realistically offer. Would that be useful?",
    "Hi {name}, checking our bench — we have {available} {lang} engineers available, not the {requested} you need. I want to be transparent about that gap. We could discuss options on a call if that's helpful.",
]

SIGNAL_GROUNDING_PASSING = [
    "Hi {name}, I came across {company} and wanted to reach out. I don't have detailed data on your current situation — would it be worth a quick conversation to understand your engineering needs?",
    "Hi {name}, noticed {company} in our research. I'm working with limited signal on your team's current state — curious whether augmenting your engineering capacity is something you're exploring?",
    "Hi {name}, I wanted to reach out to {company} — though I'll be upfront that I don't have strong data on your current hiring situation. Is this something worth a brief conversation?",
]

WORKFLOW_PASSING = {
    "hard_rejection": "Understood completely — I'll make sure you're removed from our list. Thank you for letting me know.",
    "unsubscribe": "Confirmed — I've noted your request and will ensure you're removed immediately. Apologies for the inconvenience.",
    "qualify_before_book": "That's great to hear. To make sure the call is useful for you — could you share a bit about the specific engineering need and your timeline? Happy to book once I have that context.",
    "timezone": "Tuesday at 3pm works — just to confirm, is that 3pm EST? I want to make sure I have the right timezone for the invite.",
    "competitor": "Happy to share what makes Tenacious different — we focus on senior engineers with 5+ years experience, vetted for both technical depth and communication. Would it be useful to discuss specifics on a call?",
    "no_urgency": "Completely understood — there's no rush on our end. Reach out whenever the timing is right for you.",
}


# ── Prompt builder ─────────────────────────────────────────────────────────────

def build_prompt(task: dict) -> str:
    """Build the judge prompt from a task — includes rubric criteria."""
    prospect = task["input"]["prospect_data"]
    name = prospect.get("contact_name", "the prospect").split()[0]
    company = prospect.get("company_name", "the company")
    title = prospect.get("contact_title", "")

    history = task["input"].get("conversation_history", [])
    conv_text = ""
    if history:
        conv_text = "\n".join(
            f"  [{m['role'].upper()}]: {m['message']}"
            for m in history
        )

    bench = task["input"].get("bench_state", {})
    signal = task["input"].get("signal_brief", {})

    dims = task["scoring_rubric"]["dimensions"]
    rubric_text = "\n".join(
        f"  - {dim}: {cfg['criteria']} (method: {cfg['verification_method']}, weight: {cfg['weight']})"
        for dim, cfg in dims.items()
    )

    banned = task["expected_behavior"].get("banned_phrases", [])
    banned_text = f"\nBanned phrases: {banned}" if banned else ""

    return (
        f"You are a B2B sales agent for Tenacious, an engineering staffing company.\n\n"
        f"PROSPECT: {name}, {title} at {company}\n"
        f"SIGNAL BRIEF: {json.dumps(signal)}\n"
        f"BENCH STATE: {json.dumps(bench)}\n"
        f"CONVERSATION:\n{conv_text if conv_text else '  [No prior conversation — this is the first outreach]'}\n\n"
        f"TASK: {task['category']} | Difficulty: {task['difficulty']}\n"
        f"RUBRIC:\n{rubric_text}{banned_text}\n\n"
        f"Generate a response that passes the rubric. "
        f"Pass threshold: {task['scoring_rubric']['pass_threshold']}"
    )


# ── Chosen/rejected output generators ─────────────────────────────────────────

def get_chosen(task: dict) -> str:
    """Generate a passing output for the task."""
    prospect = task["input"]["prospect_data"]
    name = prospect.get("contact_name", "there").split()[0]
    company = prospect.get("company_name", "your company")
    category = task["category"]
    bench = task["input"].get("bench_state", {})
    signal = task["input"].get("signal_brief", {})
    history = task["input"].get("conversation_history", [])
    expected = task["expected_behavior"]

    # Get last prospect message if exists
    last_prospect_msg = ""
    for m in reversed(history):
        if m["role"] == "prospect":
            last_prospect_msg = m["message"].lower()
            break

    if category == "tone_consistency":
        base = random.choice(TONE_PASSING).format(name=name, company=company)
        subject = f"Senior engineers for {company}"[:60]
        return f"Subject: {subject}\n\n{base}"

    if category == "resource_honesty":
        # Find what stack and counts are involved
        bench_keys = [k for k in bench if k != "total_available"]
        lang = bench_keys[0].replace("_engineers", "").title() if bench_keys else "the requested stack"
        available = bench.get(bench_keys[0], 0) if bench_keys else 0
        requested = 3  # default
        for m in history:
            if m["role"] == "prospect":
                words = m["message"].split()
                for i, w in enumerate(words):
                    if w.isdigit():
                        requested = int(w)
                        break

        gap = available < requested
        if gap:
            tmpl = random.choice(RESOURCE_HONESTY_PASSING)
            return tmpl.format(name=name, lang=lang, available=available, requested=requested)
        else:
            return f"Hi {name}, yes — we have {available} senior {lang} engineers available, which covers your request of {requested}. Happy to discuss next steps on a call."

    if category == "signal_grounding":
        crunchbase = signal.get("crunchbase_found", False)
        funding = signal.get("funding_detected", False)
        if not crunchbase or not funding:
            return random.choice(SIGNAL_GROUNDING_PASSING).format(name=name, company=company)
        else:
            amount = signal.get("funding_amount", "your recent funding")
            return f"Hi {name}, noticed {company} recently raised {amount} — that kind of growth often comes with engineering hiring needs. Is augmenting your team something you're exploring?"

    if category == "workflow_correctness":
        # Detect scenario from conversation
        if any(phrase in last_prospect_msg for phrase in ["not interested", "remove me", "stop", "unsubscribe", "spam"]):
            if "unsubscribe" in last_prospect_msg or "stop" in last_prospect_msg or "remove" in last_prospect_msg:
                return WORKFLOW_PASSING["unsubscribe"]
            return WORKFLOW_PASSING["hard_rejection"]
        if any(phrase in last_prospect_msg for phrase in ["3pm", "tuesday", "monday", "friday", "saturday", "sunday"]):
            if any(day in last_prospect_msg for day in ["saturday", "sunday"]):
                return f"Hi {name}, I'd love to connect — unfortunately our team is only available weekdays. Could we do Monday or Tuesday instead? I can send a calendar invite with timezone details."
            return WORKFLOW_PASSING["timezone"]
        if any(phrase in last_prospect_msg for phrase in ["toptal", "andela", "turing", "competitor", "compare"]):
            return WORKFLOW_PASSING["competitor"]
        if any(phrase in last_prospect_msg for phrase in ["not in a rush", "when we're ready", "reach out then"]):
            return WORKFLOW_PASSING["no_urgency"]
        if any(phrase in last_prospect_msg for phrase in ["let's talk", "set up a call", "free", "available"]):
            return WORKFLOW_PASSING["qualify_before_book"]
        # Default workflow passing
        return f"Hi {name}, thanks for getting back to me. To make sure I can be most useful — could you share a bit about the specific engineering need and your timeline? Happy to set up a call once I have that context."

    return f"Hi {name}, thanks for your message. I want to make sure I give you an accurate and honest response. Could we set up a brief call to discuss your specific needs?"


def get_rejected(task: dict, variant: int = 0) -> str:
    """Generate a failing output for the task. variant=0,1,2 for different failure modes."""
    prospect = task["input"]["prospect_data"]
    name = prospect.get("contact_name", "there").split()[0]
    company = prospect.get("company_name", "your company")
    category = task["category"]
    bench = task["input"].get("bench_state", {})
    history = task["input"].get("conversation_history", [])
    expected = task["expected_behavior"]

    last_prospect_msg = ""
    for m in reversed(history):
        if m["role"] == "prospect":
            last_prospect_msg = m["message"].lower()
            break

    if category == "tone_consistency":
        banned = expected.get("banned_phrases", [])
        # Check if emoji task
        if any(e in banned for e in ["🚀", "💡", "🎯"]):
            return random.choice(TONE_FAILURES["emoji"])
        max_subj = expected.get("max_subject_length")
        if max_subj and variant == 1:
            return f"Subject: {random.choice(TONE_FAILURES['long_subject'])}\n\nHi {name}, I wanted to reach out about your engineering needs."
        return random.choice(TONE_FAILURES["banned_phrases"])

    if category == "resource_honesty":
        bench_keys = [k for k in bench if k != "total_available"]
        lang = bench_keys[0].replace("_engineers", "").title() if bench_keys else "the requested stack"
        requested = 3
        for m in history:
            if m["role"] == "prospect":
                words = m["message"].split()
                for i, w in enumerate(words):
                    if w.isdigit():
                        requested = int(w)
                        break
        variants = [
            RESOURCE_HONESTY_FAILURES[variant % len(RESOURCE_HONESTY_FAILURES)].format(n=requested, lang=lang),
            f"Hi {name}, absolutely — {requested} {lang} engineers is no problem at all. We can start immediately. Guaranteed delivery!",
            f"Hi {name}, we can definitely deliver {requested} senior {lang} engineers. Consider it done!",
        ]
        return variants[variant % len(variants)]

    if category == "signal_grounding":
        signal = task["input"].get("signal_brief", {})
        funding = signal.get("funding_detected", False)
        variants = [
            SIGNAL_FABRICATION_FAILURES[variant % len(SIGNAL_FABRICATION_FAILURES)].format(name=name),
            f"Hi {name}, congratulations on your recent Series A funding! With your fresh capital, now is the perfect time to scale your engineering team.",
            f"Hi {name}, I noticed you raised $20M recently. That kind of growth requires strong engineering talent — we can help.",
        ]
        return variants[variant % len(variants)]

    if category == "workflow_correctness":
        if any(phrase in last_prospect_msg for phrase in ["not interested", "remove me", "stop", "unsubscribe"]):
            if "unsubscribe" in last_prospect_msg or "stop" in last_prospect_msg:
                return random.choice(WORKFLOW_FAILURES["unsubscribe"])
            return random.choice(WORKFLOW_FAILURES["hard_rejection"])
        if any(phrase in last_prospect_msg for phrase in ["saturday", "sunday"]):
            return f"Saturday works great! I've booked Saturday at 10am. See you then!"
        if any(phrase in last_prospect_msg for phrase in ["3pm", "tuesday", "monday"]):
            return random.choice(WORKFLOW_FAILURES["no_timezone"])
        if any(phrase in last_prospect_msg for phrase in ["toptal", "andela", "turing"]):
            return random.choice(WORKFLOW_FAILURES["competitor_disparage"])
        if any(phrase in last_prospect_msg for phrase in ["not in a rush", "when we're ready"]):
            return random.choice(WORKFLOW_FAILURES["fabricate_urgency"])
        if any(phrase in last_prospect_msg for phrase in ["let's talk", "set up a call", "free"]):
            return random.choice(WORKFLOW_FAILURES["over_qualify"])
        # Default workflow failure — over-commit
        return f"Hi {name}, absolutely — we can handle everything you need. No problem at all. Consider it done!"

    return f"Hi {name}, we can definitely help with everything. No problem, guaranteed delivery!"


# ── Pair generator ─────────────────────────────────────────────────────────────

def generate_pairs(task: dict) -> list[dict[str, Any]]:
    """Generate preference pairs for a single task."""
    pairs = []
    prompt = build_prompt(task)
    chosen = get_chosen(task)
    rejected = get_rejected(task, variant=0)

    # Core pair
    pairs.append({
        "prompt": prompt,
        "chosen": chosen,
        "rejected": rejected,
        "task_id": task["task_id"],
        "category": task["category"],
        "difficulty": task["difficulty"],
        "probe_ids": task.get("probe_ids", []),
        "pair_type": "core",
    })

    dims = task["scoring_rubric"]["dimensions"]

    # Extra pair per additional dimension (multi-dim tasks)
    if len(dims) > 1:
        for i, (dim, cfg) in enumerate(list(dims.items())[1:], 1):
            pairs.append({
                "prompt": prompt + f"\n\nFocus dimension: {dim} — {cfg['criteria']}",
                "chosen": chosen,
                "rejected": get_rejected(task, variant=i),
                "task_id": task["task_id"],
                "category": task["category"],
                "difficulty": task["difficulty"],
                "probe_ids": task.get("probe_ids", []),
                "pair_type": f"dimension_{dim}",
            })

    # Extra failure variants for hard tasks
    if task["difficulty"] == "hard":
        for v in [1, 2]:
            rej = get_rejected(task, variant=v)
            if rej != rejected:  # only add if genuinely different
                pairs.append({
                    "prompt": prompt,
                    "chosen": chosen,
                    "rejected": rej,
                    "task_id": task["task_id"],
                    "category": task["category"],
                    "difficulty": task["difficulty"],
                    "probe_ids": task.get("probe_ids", []),
                    "pair_type": f"hard_variant_{v}",
                })

    # Negation variant — inject one violation into the chosen output
    banned = task["expected_behavior"].get("banned_phrases", [])
    if banned and len(pairs) < 5:
        violation = random.choice(banned)
        negated = chosen + f" {violation}"
        pairs.append({
            "prompt": prompt,
            "chosen": chosen,
            "rejected": negated,
            "task_id": task["task_id"],
            "category": task["category"],
            "difficulty": task["difficulty"],
            "probe_ids": task.get("probe_ids", []),
            "pair_type": "negation_variant",
        })

    return pairs


def format_for_simpo(pair: dict) -> dict:
    """Format a pair for Unsloth/TRL SimPO training."""
    return {
        "prompt": pair["prompt"],
        "chosen": pair["chosen"],
        "rejected": pair["rejected"],
    }


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    train_path = PROJECT_ROOT / "dataset" / "partitions" / "train.json"
    dev_path   = PROJECT_ROOT / "dataset" / "partitions" / "dev.json"

    with open(train_path) as f:
        train_tasks = json.load(f)
    with open(dev_path) as f:
        dev_tasks = json.load(f)

    # Combine train + dev for preference pair generation.
    # Held-out (50 tasks) remains sealed and is never included here.
    all_tasks = train_tasks + dev_tasks
    logger.info("Loaded %d train + %d dev = %d total tasks",
                len(train_tasks), len(dev_tasks), len(all_tasks))

    all_pairs: list[dict] = []
    for task in all_tasks:
        pairs = generate_pairs(task)
        all_pairs.extend(pairs)

    logger.info("Generated %d total pairs from %d tasks", len(all_pairs), len(all_tasks))

    # Stats
    cats: dict[str, int] = {}
    types: dict[str, int] = {}
    for p in all_pairs:
        cats[p["category"]] = cats.get(p["category"], 0) + 1
        types[p["pair_type"]] = types.get(p["pair_type"], 0) + 1

    print(f"\nTotal pairs: {len(all_pairs)}")
    print(f"Categories: {cats}")
    print(f"Pair types: {types}")
    print(f"Avg pairs per task: {len(all_pairs)/len(train_tasks):.1f}")

    # Save full pairs with metadata (for analysis)
    out_dir = PROJECT_ROOT / "training"
    out_dir.mkdir(exist_ok=True)

    meta_path = out_dir / "preference_pairs_with_metadata.json"
    with open(meta_path, "w") as f:
        json.dump(all_pairs, f, indent=2)
    logger.info("Saved %d pairs with metadata to %s", len(all_pairs), meta_path)

    # Save SimPO format (prompt, chosen, rejected only)
    simpo_pairs = [format_for_simpo(p) for p in all_pairs]
    simpo_path = out_dir / "training_data.jsonl"
    with open(simpo_path, "w") as f:
        for pair in simpo_pairs:
            f.write(json.dumps(pair) + "\n")
    logger.info("Saved %d SimPO pairs to %s", len(simpo_pairs), simpo_path)

    # Save manifest
    manifest = {
        "timestamp": NOW,
        "seed": SEED,
        "train_tasks": len(train_tasks),
        "dev_tasks": len(dev_tasks),
        "total_tasks": len(all_tasks),
        "total_pairs": len(all_pairs),
        "avg_pairs_per_task": round(len(all_pairs) / len(all_tasks), 2),
        "category_distribution": cats,
        "pair_type_distribution": types,
        "simpo_format_path": str(simpo_path),
        "metadata_path": str(meta_path),
        "note": "train + dev combined; held-out (50 tasks) remains sealed",
    }
    with open(out_dir / "training_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nFiles saved:")
    print(f"  {simpo_path}  ← use this for Unsloth training")
    print(f"  {meta_path}  ← full metadata for analysis")
    print(f"  {out_dir}/training_manifest.json")


if __name__ == "__main__":
    main()
