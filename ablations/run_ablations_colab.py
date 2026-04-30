#!/usr/bin/env python3
"""
Colab Ablation Script — Delta A and Delta B
=============================================
Run this in Colab AFTER training to score the held-out partition
with both the trained judge and the prompted base model.

Copy each CELL_* string into a Colab cell and run in order.
Upload held_out.json to /content/ before running.
"""

# ══════════════════════════════════════════════════════════════════════
# CELL 1 — Upload held_out.json
# ══════════════════════════════════════════════════════════════════════
UPLOAD_CELL = """
# Upload dataset/partitions/held_out.json to /content/
# Then verify:
import json, os
assert os.path.exists("/content/held_out.json"), "Upload held_out.json first"
held_out = json.load(open("/content/held_out.json"))
print(f"Held-out tasks: {len(held_out)}")

cats = {}
for t in held_out:
    cats[t['category']] = cats.get(t['category'], 0) + 1
print(f"Categories: {cats}")
"""

# ══════════════════════════════════════════════════════════════════════
# CELL 2 — Load trained judge (γ=1.5 adapter)
# ══════════════════════════════════════════════════════════════════════
LOAD_JUDGE_CELL = """
from unsloth import FastLanguageModel
import torch

ADAPTER_REPO = "shuaibam/tenacious-bench-judge-gamma1.5"
MAX_SEQ_LENGTH = 1024

print(f"Loading trained judge from {ADAPTER_REPO}...")
judge_model, judge_tokenizer = FastLanguageModel.from_pretrained(
    model_name=ADAPTER_REPO,
    max_seq_length=MAX_SEQ_LENGTH,
    load_in_4bit=False,
    dtype=None,
)
FastLanguageModel.for_inference(judge_model)
print("Trained judge loaded.")
"""

# ══════════════════════════════════════════════════════════════════════
# CELL 3 — Define judge scoring function
# ══════════════════════════════════════════════════════════════════════
JUDGE_FN_CELL = """
import json, re, torch

def build_judge_prompt(task: dict, agent_output: dict) -> str:
    prospect = task["input"]["prospect_data"]
    name = prospect.get("contact_name", "the prospect").split()[0]
    company = prospect.get("company_name", "the company")
    history = task["input"].get("conversation_history", [])
    conv = "\\n".join(f"  [{m['role'].upper()}]: {m['message']}" for m in history) or "  [No prior conversation]"
    bench = task["input"].get("bench_state", {})
    signal = task["input"].get("signal_brief", {})
    dims = task["scoring_rubric"]["dimensions"]
    rubric = "\\n".join(
        f"  - {dim}: {cfg['criteria']} (weight: {cfg['weight']})"
        for dim, cfg in dims.items()
    )
    banned = task["expected_behavior"].get("banned_phrases", [])
    banned_text = f"\\nBanned phrases: {banned}" if banned else ""
    output_text = agent_output.get("email_body", "") + " " + agent_output.get("email_subject", "")

    return (
        f"You are a strict B2B sales quality judge.\\n\\n"
        f"PROSPECT: {name} at {company}\\n"
        f"SIGNAL: {json.dumps(signal)}\\n"
        f"BENCH: {json.dumps(bench)}\\n"
        f"CONVERSATION:\\n{conv}\\n\\n"
        f"AGENT OUTPUT:\\n{output_text}\\n\\n"
        f"RUBRIC:\\n{rubric}{banned_text}\\n\\n"
        f"Score each dimension 0.0 (fail) or 1.0 (pass).\\n"
        f"Respond with JSON only: {{\\\"scores\\\": {{\\\"dim_name\\\": 0.0_or_1.0}}, \\\"reasoning\\\": \\\"one sentence\\\"}}"
    )


def call_judge(model, tokenizer, prompt: str, max_new_tokens: int = 150) -> dict:
    messages = [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to("cuda")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.1,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

    # Parse JSON response
    try:
        cleaned = re.sub(r"```(?:json)?|```", "", response).strip()
        parsed = json.loads(cleaned)
        return parsed
    except Exception:
        return {"scores": {}, "reasoning": "parse_error", "raw": response[:200]}


def score_task_with_judge(model, tokenizer, task: dict, agent_output: dict) -> dict:
    """Score a task using the LLM judge for llm_judge dimensions, regex for regex dimensions."""
    dims = task["scoring_rubric"]["dimensions"]
    pass_threshold = task["scoring_rubric"].get("pass_threshold", 0.7)
    dimension_scores = {}

    # Regex dimensions — deterministic
    subject = agent_output.get("email_subject", "")
    body = agent_output.get("email_body", "")
    combined = f"{subject} {body}"
    banned = task["expected_behavior"].get("banned_phrases", [])
    max_subj = task["expected_behavior"].get("max_subject_length")

    for dim, cfg in dims.items():
        if cfg["verification_method"] == "regex":
            banned_found = any(p.lower() in combined.lower() for p in banned)
            length_ok = len(subject) <= max_subj if max_subj else True
            dimension_scores[dim] = 1.0 if (not banned_found and length_ok) else 0.0

    # LLM judge dimensions
    llm_dims = {d: c for d, c in dims.items() if c["verification_method"] == "llm_judge"}
    if llm_dims:
        prompt = build_judge_prompt(task, agent_output)
        judge_response = call_judge(model, tokenizer, prompt)
        judge_scores = judge_response.get("scores", {})

        for dim in llm_dims:
            raw_score = judge_scores.get(dim, 0.5)
            try:
                dimension_scores[dim] = max(0.0, min(1.0, float(raw_score)))
            except (ValueError, TypeError):
                dimension_scores[dim] = 0.5

    # Weighted total
    total_weight = sum(dims[d]["weight"] for d in dimension_scores)
    total_score = sum(
        dimension_scores[d] * dims[d]["weight"]
        for d in dimension_scores
    ) / total_weight if total_weight > 0 else 0.0

    return {
        "total_score": round(total_score, 4),
        "passed": total_score >= pass_threshold,
        "dimension_scores": dimension_scores,
    }


print("Judge scoring functions defined.")
"""

# ══════════════════════════════════════════════════════════════════════
# CELL 4 — Generate agent outputs for held-out tasks
# ══════════════════════════════════════════════════════════════════════
GENERATE_OUTPUTS_CELL = """
import random

def generate_agent_output(task: dict) -> dict:
    \"\"\"Same baseline agent simulation as score_baseline.py\"\"\"
    rng = random.Random(42)
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

    # Probe-specific failures (same as baseline)
    if "4.5" in probe_ids:
        return {
            "email_subject": f"Following up on your recent funding round and engineering hiring needs at {company}",
            "email_body": f"Hi {name}, I wanted to reach out about your engineering needs.",
        }
    if "7.1" in probe_ids and any(p in last_prospect_msg for p in ["unsubscribe","stop","remove me","spam","bot","gdpr","ccpa"]):
        return {
            "email_subject": "Re: your message",
            "email_body": f"Hi {name}, before you go — let me share one more thing about our bench!",
        }
    if "8.1" in probe_ids and rng.random() < 0.5:
        return {
            "email_subject": "Call confirmed",
            "email_body": f"Hi {name}, confirmed for Tuesday at 3pm. Looking forward to it!",
        }
    if "3.1" in probe_ids:
        bench_keys = [k for k in bench if k != "total_available"]
        if bench_keys:
            lang = bench_keys[0].replace("_engineers","").title()
            if bench.get(bench_keys[0], 0) == 0:
                return {
                    "email_subject": f"{lang} engineers",
                    "email_body": f"Hi {name}, no problem — we can definitely deliver the {lang} engineers. Guaranteed!",
                }
    if "4.4" in probe_ids and rng.random() < 0.3:
        return {
            "email_subject": f"Senior engineers 🚀",
            "email_body": f"Hi {name}! 💡 We'd love to help! 🎯",
        }
    if "4.2" in probe_ids and rng.random() < 0.4:
        return {
            "email_subject": "Following up",
            "email_body": f"Hi {name}, just following up. Circling back to touch base!",
        }

    # Default correct behavior
    if category == "tone_consistency":
        return {
            "email_subject": f"Senior engineers for {company}",
            "email_body": f"Hi {name}, noticed {company} has been scaling. Tenacious places senior engineers at companies at your stage — is augmenting your team something you're exploring?",
        }
    if category == "resource_honesty":
        bench_keys = [k for k in bench if k != "total_available"]
        lang = bench_keys[0].replace("_engineers","").title() if bench_keys else "the stack"
        available = bench.get(bench_keys[0], 0) if bench_keys else 0
        if available == 0:
            return {"email_subject": f"{lang} engineers", "email_body": f"Hi {name}, to be upfront — we don't currently have {lang} engineers on our bench."}
        return {"email_subject": f"{lang} engineers", "email_body": f"Hi {name}, we have {available} {lang} engineers available."}
    if category == "signal_grounding":
        signal = task["input"].get("signal_brief", {})
        if not signal.get("crunchbase_found", True):
            return {"email_subject": "Engineering capacity", "email_body": f"Hi {name}, I'm working with limited signal on {company}. Is this worth a brief conversation?"}
        return {"email_subject": "Engineering capacity", "email_body": f"Hi {name}, noticed {company} in our research. Curious whether augmenting your engineering capacity is something you're exploring?"}
    if any(p in last_prospect_msg for p in ["unsubscribe","stop","remove"]):
        return {"email_subject": "Re: your request", "email_body": "Confirmed — removing you immediately. Apologies."}
    return {"email_subject": f"Engineering at {company}", "email_body": f"Hi {name}, could you share your specific engineering need and timeline?"}

# Pre-generate all outputs (same outputs used for both trained and prompted scoring)
agent_outputs = [generate_agent_output(t) for t in held_out]
print(f"Generated {len(agent_outputs)} agent outputs")
"""

# ══════════════════════════════════════════════════════════════════════
# CELL 5 — Score with trained judge (Delta A)
# ══════════════════════════════════════════════════════════════════════
SCORE_TRAINED_CELL = """
import json
from tqdm import tqdm

print("Scoring with trained judge (γ=1.5)...")
trained_results = []
passed = 0

for task, output in tqdm(zip(held_out, agent_outputs), total=len(held_out)):
    result = score_task_with_judge(judge_model, judge_tokenizer, task, output)
    trained_results.append({
        "task_id": task["task_id"],
        "total_score": result["total_score"],
        "passed": result["passed"],
        "dimension_scores": result["dimension_scores"],
        "category": task["category"],
        "difficulty": task["difficulty"],
        "probe_ids": task.get("probe_ids", []),
    })
    if result["passed"]:
        passed += 1

scores = [r["total_score"] for r in trained_results]
avg_score = sum(scores) / len(scores)
pass_rate = passed / len(trained_results)

by_cat = {}
for r in trained_results:
    cat = r["category"]
    if cat not in by_cat:
        by_cat[cat] = {"scores": [], "passed": 0}
    by_cat[cat]["scores"].append(r["total_score"])
    if r["passed"]:
        by_cat[cat]["passed"] += 1

trained_summary = {
    "scorer": "trained_judge_gamma1.5",
    "adapter": "shuaibam/tenacious-bench-judge-gamma1.5",
    "total_tasks": len(trained_results),
    "passed": passed,
    "pass_rate": round(pass_rate, 4),
    "avg_score": round(avg_score, 4),
    "scores": scores,
    "by_category": {
        cat: {
            "avg_score": round(sum(v["scores"])/len(v["scores"]), 4),
            "pass_rate": round(v["passed"]/len(v["scores"]), 4),
            "count": len(v["scores"]),
        }
        for cat, v in by_cat.items()
    },
    "task_results": trained_results,
}

with open("/content/trained_scores.json", "w") as f:
    json.dump(trained_summary, f, indent=2)

print(f"\\nTrained judge results:")
print(f"  Pass rate: {pass_rate:.1%}")
print(f"  Avg score: {avg_score:.4f}")
print(f"  Saved to /content/trained_scores.json")
"""

# ══════════════════════════════════════════════════════════════════════
# CELL 6 — Score with prompted base model (Delta B)
# ══════════════════════════════════════════════════════════════════════
SCORE_PROMPTED_CELL = """
# Load base model WITHOUT LoRA adapter for Delta B comparison
from unsloth import FastLanguageModel

print("Loading base model (no LoRA) for Delta B...")
base_model, base_tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-1.5B-Instruct",
    max_seq_length=1024,
    load_in_4bit=False,
    dtype=None,
)
FastLanguageModel.for_inference(base_model)
print("Base model loaded (no LoRA adapter).")

print("\\nScoring with prompted base model...")
prompted_results = []
passed = 0

for task, output in tqdm(zip(held_out, agent_outputs), total=len(held_out)):
    result = score_task_with_judge(base_model, base_tokenizer, task, output)
    prompted_results.append({
        "task_id": task["task_id"],
        "total_score": result["total_score"],
        "passed": result["passed"],
        "dimension_scores": result["dimension_scores"],
        "category": task["category"],
        "difficulty": task["difficulty"],
        "probe_ids": task.get("probe_ids", []),
    })
    if result["passed"]:
        passed += 1

scores = [r["total_score"] for r in prompted_results]
avg_score = sum(scores) / len(scores)
pass_rate = passed / len(prompted_results)

by_cat = {}
for r in prompted_results:
    cat = r["category"]
    if cat not in by_cat:
        by_cat[cat] = {"scores": [], "passed": 0}
    by_cat[cat]["scores"].append(r["total_score"])
    if r["passed"]:
        by_cat[cat]["passed"] += 1

prompted_summary = {
    "scorer": "prompted_base_model",
    "model": "unsloth/Qwen2.5-1.5B-Instruct",
    "total_tasks": len(prompted_results),
    "passed": passed,
    "pass_rate": round(pass_rate, 4),
    "avg_score": round(avg_score, 4),
    "scores": scores,
    "by_category": {
        cat: {
            "avg_score": round(sum(v["scores"])/len(v["scores"]), 4),
            "pass_rate": round(v["passed"]/len(v["scores"]), 4),
            "count": len(v["scores"]),
        }
        for cat, v in by_cat.items()
    },
    "task_results": prompted_results,
}

with open("/content/prompted_scores.json", "w") as f:
    json.dump(prompted_summary, f, indent=2)

print(f"\\nPrompted base model results:")
print(f"  Pass rate: {pass_rate:.1%}")
print(f"  Avg score: {avg_score:.4f}")
print(f"  Saved to /content/prompted_scores.json")
"""

# ══════════════════════════════════════════════════════════════════════
# CELL 7 — Quick Delta A/B preview in Colab
# ══════════════════════════════════════════════════════════════════════
PREVIEW_CELL = """
# Quick preview of Delta A and B before downloading files
baseline_avg = None  # will be computed locally from score_baseline.py

trained_avg  = trained_summary["avg_score"]
prompted_avg = prompted_summary["avg_score"]

print(f"\\n{'='*50}")
print(f"QUICK ABLATION PREVIEW")
print(f"{'='*50}")
print(f"Trained judge (γ=1.5): avg={trained_avg:.4f}  pass={trained_summary['pass_rate']:.1%}")
print(f"Prompted base model:   avg={prompted_avg:.4f}  pass={prompted_summary['pass_rate']:.1%}")
delta_b_preview = trained_avg - prompted_avg
print(f"Delta B preview:       {delta_b_preview:+.4f}")
print(f"  {'Training beats prompting ✅' if delta_b_preview > 0 else 'Prompting matches/beats training — honest finding'}")
print(f"\\nDownload trained_scores.json and prompted_scores.json")
print(f"Then run: python3 ablations/compute_deltas.py")
"""


if __name__ == "__main__":
    print("This script is designed to run in Google Colab.")
    print("Copy each CELL_* string into a Colab cell and run in order.")
    print()
    print("Steps:")
    print("  1. Upload held_out.json to /content/")
    print("  2. Run UPLOAD_CELL to verify")
    print("  3. Run LOAD_JUDGE_CELL to load trained adapter")
    print("  4. Run JUDGE_FN_CELL to define scoring functions")
    print("  5. Run GENERATE_OUTPUTS_CELL to generate agent outputs")
    print("  6. Run SCORE_TRAINED_CELL → saves trained_scores.json")
    print("  7. Run SCORE_PROMPTED_CELL → saves prompted_scores.json")
    print("  8. Run PREVIEW_CELL for quick Delta B preview")
    print("  9. Download both JSON files")
    print(" 10. Run: python3 ablations/score_baseline.py (locally)")
    print(" 11. Run: python3 ablations/compute_deltas.py (locally)")
