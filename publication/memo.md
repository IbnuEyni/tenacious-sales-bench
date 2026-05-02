# Memo: Tenacious-Bench v0.1 — Evaluation Results and Deployment Recommendation

**To:** Tenacious CEO and CFO | **From:** IbnuEyni | **Date:** 2026-04-30

---

## Page 1 — The Decision

### Executive Summary

We built Tenacious-Bench v0.1 — 250 machine-verifiable evaluation tasks covering the full B2B sales pipeline — and trained a SimPO preference judge (Qwen2.5-1.5B-Instruct, LoRA rank=16, 599 pairs, γ=1.5) to serve as an automated quality gate before any agent output reaches a prospect. The trained judge improves over the heuristic baseline by Delta A = +0.043 (95% CI: −0.012 to +0.103, p=0.065), a positive but not yet statistically significant result at p<0.05 that indicates the minimum viable training dataset is ~800–1,000 pairs. Recommendation: deploy the benchmark and prompted judge immediately; retrain the judge at ~1,000 pairs from production traces to achieve significance.

### Headline Numbers

| Metric | Baseline | Trained Judge | Prompted Judge |
|---|---|---|---|
| Pass rate | 34.0% | 30.0% | 58.0% |
| Avg score | 0.525 | 0.568 | 0.647 |
| Latency/task | 0.001s | 1.37s | 1.54s |
| Cost/task | $0.000 | $0.000* | $0.000* |
| Delta A | — | **+0.043, p=0.065, CI[−0.012,+0.103]** | — |
| Delta B | — | **−0.079 vs prompted** | — |

*$0 on Colab T4; ~$0.0005/task on RunPod 4090 ($0.34/hr).

### Delta B — Honest Finding

The prompted base model (no LoRA, rubric prompt only) achieved 58% pass rate vs the trained judge's 30% — Delta B = −0.079. At 599 pairs, training does not beat prompting. The effect size doubled from run 1 (370 pairs, Δ=+0.019) to run 2 (599 pairs, Δ=+0.043), confirming a scaling trend. Extrapolating, ~800–1,000 pairs should cross p<0.05. If Delta B remains negative after retraining at 1,000 pairs, the trained judge should be abandoned permanently in favor of the prompted baseline.

### Cost per Task Delta and Production Implication

The trained judge is 1,370× slower than the heuristic baseline (1.37s vs 0.001s) for only +0.043 score improvement. At $0.34/hr on RunPod 4090, 1.37s/task translates to **$0.00013/task** for the trained judge vs **$0.000001/task** for the heuristic — a 130× cost increase per evaluation for a gain that is not yet statistically significant. The prompted judge costs the same ($0.00015/task at 1.54s) but delivers +0.122 score improvement and +24pp pass rate — a 8× better quality-per-dollar ratio than the trained judge. **Production implication:** at 60 outbound emails/week, the prompted judge costs ~$0.009/week on paid GPU — under $0.50/year — while delivering the highest quality lift of the three options. The trained LoRA judge costs the same but underperforms; it should not be deployed until Delta A reaches significance.

### Deployment Recommendation

**Deploy the benchmark immediately** — Tenacious-Bench v0.1 is the evaluation standard for all agent outputs. Condition: run `python3 validate_tasks.py` to confirm 250/250 tasks valid before each release.

**Deploy the prompted judge as interim quality gate** — 58% pass rate, $0 cost, 1.54s latency. Condition: maintain until Delta A reaches p<0.05 on a retrained judge at ~1,000 pairs.

**Do not deploy the trained LoRA judge** — Delta A positive but not significant (p=0.065). Condition for deployment: retrain at ~1,000 pairs from real production traces, achieve p<0.05, confirm Delta B turns positive.

---

## Page 2 — The Skeptic's Appendix

### Four Coverage Gaps for v0.2

**1. Long-horizon conversations (>8 turns):** *Present:* 1–4 turn tasks. *Missing:* 8–15 turn trajectories where tone drift and context loss compound over weeks of real sales conversations.

**2. Real prospect data distribution:** *Present:* Synthetic signal briefs with clean ground truth. *Missing:* Real Crunchbase noise — funding rounds announced but not closed, layoffs affecting one division only. Benchmark overestimates performance on genuinely ambiguous signals.

**3. High-volume multi-prospect coordination:** *Present:* 2 tasks for single-thread leakage. *Missing:* 50+ simultaneous threads — the production reality. Thread isolation failures at scale are architecturally different from single-thread failures.

**4. Regulatory compliance depth:** *Present:* 4 tasks each for GDPR, CCPA, defense, healthcare. *Missing:* 20–30 tasks per category with legal review before using the benchmark as a formal compliance gate.

### Ground Truth Faithfulness Self-Critique

**Strengths:** 29 regex-verified dimensions (subject length, banned phrases, fabrication detection) have perfect ground truth fidelity — `len(subject) <= 60` is always correct. **Limitations:** 49 llm_judge dimensions rely on rubric criteria written by a single author. Concrete example: the resource_honesty criterion says "must honestly state bench capacity" — "we don't have Rust engineers" passes; "we're not strong in Rust" is ambiguous. The inter-rater exercise (91.7% agreement) resolved 3 such ambiguities, but production edge cases will surface more. Signal_brief fields use placeholder values ("$20M Series B") rather than real Crunchbase data — the benchmark tests responses to clean signals, not the noisy real-world signals the agent actually receives.

### One Honest Unresolved Training Failure

The trained judge achieves 100% reward accuracy on training data but only 30% pass rate on held-out tasks — 4pp *below* the heuristic baseline (34%). Root cause: all 599 training pairs were generated by a deterministic Python heuristic, not the real agent. The judge learned to score the heuristic's output distribution. Concretely: the heuristic always generates "Hi {name}, to be upfront — we don't currently have {lang} engineers"; the real agent generates varied phrasings the judge has never seen. Fix for v0.2: generate preference pairs from real production agent outputs.

### Kill-Switch Trigger Conditions

Disable trained judge and revert to prompted baseline if any of the following occur:

1. Pass rate drops below **20%** on any rolling 100-task window (current baseline: 34% — 14pp buffer)
2. Any agent output containing a banned phrase receives judge score **>0.7** — calibration failure
3. Evaluation latency exceeds **3 seconds/task** (current: 1.37s — 2.2× headroom)
4. A verified prospect complaint about factual errors traces to a task the judge scored as passing

---
*Benchmark: huggingface.co/datasets/shuaibam/tenacious-bench-v0.1 | Model: huggingface.co/shuaibam/tenacious-bench-judge-v0.1 | Code: github.com/IbnuEyni/tenacious-sales-bench*
