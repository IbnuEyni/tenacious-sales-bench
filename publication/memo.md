# Memo: Tenacious-Bench v0.1 — Evaluation Results and Deployment Recommendation

**To:** Tenacious CEO and CFO
**From:** IbnuEyni
**Date:** 2026-04-30
**Re:** B2B Sales Agent Evaluation Benchmark — Results and Production Recommendation

---

## Page 1 — The Decision

### Executive Summary

We built Tenacious-Bench v0.1 — 250 machine-verifiable evaluation tasks covering the full B2B sales pipeline — and trained a SimPO preference judge (Qwen2.5-1.5B-Instruct, LoRA rank=16, 599 pairs, γ=1.5) to serve as an automated quality gate for agent outputs. The trained judge improves over the heuristic baseline by Delta A = +0.043 (95% CI: −0.012 to +0.103, p=0.065), which is positive but does not reach statistical significance at p<0.05. A well-prompted version of the same base model outperforms the trained judge (Delta B = −0.079), making prompt engineering the stronger quality gate at current data scale; recommendation is to deploy the benchmark and prompted judge immediately while collecting production traces to retrain at ~1,000 pairs.

---

### Headline Numbers

| Metric | Value |
|---|---|
| Benchmark tasks | 250 — 100% valid, contamination PASSED |
| Failure modes covered | 33 across full sales pipeline |
| Baseline pass rate (heuristic) | 34.0% — avg score 0.525 |
| Trained judge pass rate | 30.0% — avg score 0.568 |
| Prompted base model pass rate | 58.0% — avg score 0.647 |
| **Delta A** (trained vs baseline) | **+0.043, 95% CI [−0.012, +0.103], p=0.065** |
| **Delta B** (trained vs prompted) | **−0.079 — prompting beats training** |
| Baseline latency per task | 0.001s (pure Python, no GPU) |
| Trained judge latency per task | 1.37s (T4 GPU inference) |
| Prompted judge latency per task | 1.54s (T4 GPU inference) |
| Training cost | $0.00 (Colab T4, free tier) |
| Evaluation cost per task | ~$0.001 (prompted judge) |

---

### Delta B — Honest Comparison Against Prompted Baseline

The prompted base model (Qwen2.5-1.5B-Instruct, no LoRA, rubric prompt only) achieved 58% pass rate vs the trained judge's 30% — a Delta B of −0.079. This is a clear negative finding: at 599 preference pairs, training does not beat prompting. The root cause is data scale — SimPO's Appendix B tests down to ~1,000 pairs on general benchmarks; we are 40% below that minimum. The effect size doubled from run 1 (370 pairs, Δ=+0.019) to run 2 (599 pairs, Δ=+0.043), confirming the scaling trend. Extrapolating, ~800–1,000 pairs should cross the significance threshold. Delta B will be re-run after retraining at 1,000 pairs; if it remains negative at that scale, the trained judge should be abandoned in favor of the prompted baseline permanently.

---

### Cost per Task Delta and Production Implication

| Scorer | Latency | Cost/task | Pass rate | Quality (avg score) |
|---|---|---|---|---|
| Heuristic baseline | 0.001s | $0.000 | 34% | 0.525 |
| Trained judge (LoRA) | 1.37s | $0.000* | 30% | 0.568 |
| Prompted base model | 1.54s | $0.000* | 58% | 0.647 |

*$0 on Colab T4; ~$0.0005/task on RunPod 4090 at $0.34/hr.

The trained judge is 1,370× slower than the heuristic baseline but achieves only +0.043 score improvement — a poor cost-quality tradeoff at current data scale. The prompted base model is 1,540× slower than heuristic but achieves +0.122 score improvement and +24pp pass rate — a significantly better tradeoff. **Production implication:** deploy the prompted judge as the quality gate. At 60 outbound emails/week, the 1.54s latency adds 92 seconds of total evaluation time per week — negligible. The $0 cost on free GPU makes this viable immediately.

---

### Deployment Recommendation

**Deploy the benchmark now** — Tenacious-Bench v0.1 is the evaluation standard for all agent outputs. Costs $0.001/task with the prompted judge.

**Deploy the prompted judge as interim quality gate** — 58% pass rate, $0 cost, 1.54s latency. Condition: maintain this until Delta A reaches p<0.05 on a retrained judge.

**Do not deploy the trained LoRA judge** — Delta A is positive (+0.043) but not significant (p=0.065). Condition for deployment: retrain at ~1,000 pairs from real production traces, achieve p<0.05 on held-out, and confirm Delta B turns positive.

---

## Page 2 — The Skeptic's Appendix

### Four Coverage Gaps for v0.2

**1. Long-horizon conversations (>8 turns)**
*Present:* Tasks cover 1–4 turn conversations. *Missing:* 8–15 turn trajectories where tone drift and context loss compound. Real sales conversations span weeks. v0.2 needs trajectories from production logs.

**2. Real prospect data distribution**
*Present:* Synthetic signal briefs with clean pass/fail ground truth. *Missing:* Real Crunchbase noise — funding rounds announced but not closed, layoffs affecting one division only, AI maturity scores from ambiguous evidence. Benchmark overestimates agent performance on genuinely ambiguous signals.

**3. High-volume multi-prospect coordination**
*Present:* 2 tasks covering single-thread leakage (Probes 5.1, 5.2). *Missing:* 50+ simultaneous prospect threads — the production reality. Thread isolation failures at scale are architecturally different from single-thread failures.

**4. Regulatory compliance at production depth**
*Present:* 4 tasks each for GDPR, CCPA, defense, healthcare. *Missing:* 20–30 tasks per category with legal review. Current coverage is insufficient to use the benchmark as a formal compliance gate.

---

### Ground Truth Faithfulness Self-Critique

**Strengths:** The benchmark's ground truth is deterministic for hard-constraint dimensions — `len(subject) <= 60` is always correct; banned phrase detection via regex is always correct. These 29 regex-verified dimensions have perfect ground truth fidelity.

**Limitations:** The 49 llm_judge dimensions rely on rubric criteria written by a single author. Concrete example of lossiness: the resource_honesty criterion says "must honestly state bench capacity" — but what counts as honest? "We don't have Rust engineers" passes; "we're not strong in Rust" is ambiguous. The inter-rater agreement exercise (91.7%) revealed 3 such ambiguities and resolved them, but production edge cases will surface more. A second limitation: signal_brief fields use placeholder values ("$20M Series B") rather than real Crunchbase data — the benchmark tests the agent's response to clean signals, not the noisy real-world signals it will actually receive.

---

### One Honest Unresolved Training Failure

The trained judge achieves 100% reward accuracy on training data but only 30% pass rate on held-out tasks — 4 percentage points *below* the heuristic baseline (34%). This is not a rounding error; it is a systematic failure. The root cause: all 599 training preference pairs were generated by a deterministic Python heuristic (`generate_agent_output()`), not by the real Tenacious agent. The judge learned to score the heuristic's output distribution, which differs from the real agent's distribution on the held-out tasks. Concretely: the heuristic always generates "Hi {name}, to be upfront — we don't currently have {lang} engineers" for resource_honesty tasks; the real agent generates varied phrasings that the judge has never seen. This distribution mismatch is the single most important thing to fix in v0.2.

---

### Kill-Switch Trigger Conditions

Disable the trained judge and revert to prompted baseline immediately if any of the following occur:

1. **Pass rate drops below 20%** on any rolling 100-task evaluation window (current heuristic baseline: 34% — a 14pp buffer)
2. **Calibration failure:** any agent output containing a banned phrase (fabrication or over-commitment) receives a judge score >0.7 — indicates the judge is rewarding the wrong behavior
3. **Latency breach:** evaluation latency per task exceeds 3 seconds on production hardware (current: 1.37s on T4 — 2.2× headroom)
4. **Complaint trace:** a verified prospect complaint about factual errors in agent output is traced to a task the judge scored as passing — indicates real-world harm from judge miscalibration

---

*Benchmark: https://huggingface.co/datasets/shuaibam/tenacious-bench-v0.1*
*Model: https://huggingface.co/shuaibam/tenacious-bench-judge-v0.1*
*Code: https://github.com/IbnuEyni/tenacious-sales-bench*
*Blog: https://open.substack.com/pub/shuaibi/p/building-a-domain-specific-benchmark*
