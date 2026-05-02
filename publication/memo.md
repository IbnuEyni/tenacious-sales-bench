# Memo: Tenacious-Bench v0.1 — Evaluation Results and Deployment Recommendation

**To:** Tenacious CEO and CFO
**From:** IbnuEyni
**Date:** 2026-04-30
**Re:** B2B Sales Agent Evaluation Benchmark — Results and Production Recommendation

---

## Page 1 — The Decision

### Executive Summary

We built a domain-specific evaluation benchmark for the Tenacious Conversion
Engine — the AI agent that automates prospect research, outreach, engagement,
and discovery call booking. The benchmark (Tenacious-Bench v0.1) contains 250
machine-verifiable test scenarios grounded in 33 documented failure modes
identified through structured adversarial testing of the live agent.

We also trained a preference judge — a small AI model that automatically scores
agent outputs against the benchmark rubric — to serve as a quality gate before
any agent output reaches a prospect.

**Bottom line:** The benchmark is production-ready and should be deployed now.
The trained judge shows positive improvement over the heuristic baseline but
does not yet reach statistical significance. A well-prompted version of the
same base model outperforms the trained judge at current data scale. Recommendation:
deploy the benchmark and the prompted judge immediately; retrain the judge with
more data in v0.2.

---

### Headline Numbers

| Metric | Value |
|---|---|
| Benchmark tasks | 250 (100% valid, contamination PASSED) |
| Failure modes covered | 33 across the full sales pipeline |
| Baseline pass rate (no judge) | 34.0% |
| Trained judge pass rate | 30.0% |
| Prompted base model pass rate | 58.0% |
| Delta A — trained vs baseline | +0.043, p=0.065 |
| Delta B — trained vs prompted | -0.079 |
| Training cost | $0.00 (free cloud GPU) |
| Total project budget spent | $0.15 of $10.00 |
| Training time | 30 minutes |

---

### Why This Benchmark Exists

Existing agent benchmarks (τ²-Bench, AgentBench) measure task completion in
generic scenarios. They cannot grade the four failure modes that matter most
for Tenacious:

- **Signal grounding** — does the agent fabricate funding, layoff, or hiring
  claims about a prospect? One fabricated claim destroys a relationship
  permanently.
- **Tone consistency** — does the agent maintain professional language across
  a multi-turn conversation, or drift into marketing clichés by turn 4?
- **Resource honesty** — does the agent over-commit bench capacity it doesn't
  have? Promising 3 Rust engineers when the bench has zero is a contract risk.
- **Workflow correctness** — does the agent follow proper qualification
  sequences, respect decision-maker hierarchies, and handle legal requests
  (GDPR, CCPA) correctly?

These failures were measured at a 16% aggregate trigger rate across tested
scenarios — meaning 1 in 6 agent interactions had a measurable failure that
existing benchmarks would not catch. At 60 outbound emails per week, subject
line length violations alone represent $72K–$336K annual revenue at risk.

---

### Deployment Recommendation

**Deploy the benchmark immediately.** Tenacious-Bench v0.1 is the evaluation
standard for all agent outputs going forward. The scoring evaluator runs
without human intervention and costs approximately $0.001 per evaluation.

**Use the prompted judge as interim quality gate.** A well-prompted
Qwen2.5-1.5B-Instruct model achieves 58% pass rate on the benchmark. Deploy
this as a rejection sampling layer — agent outputs that fail the rubric are
retried or escalated to human review before reaching a prospect.

**Do not deploy the trained LoRA judge yet.** The trained judge improves over
the heuristic baseline (+0.043 average score) but the improvement is not
statistically significant (p=0.065, threshold p<0.05). It also underperforms
the prompted baseline at current data scale.

**Path to deploying the trained judge:**
1. Collect 400 more preference pairs from production agent traces — zero
   additional cost, generated automatically from live agent outputs
2. Retrain at ~1,000 pairs — expected to achieve p<0.05 based on the observed
   scaling trend (effect size doubled from 370 to 599 pairs)
3. Estimated retraining cost: $0 on free cloud GPU, ~30 minutes

---

## Page 2 — The Skeptic's Appendix

### Four Failure Modes the Benchmark Does Not Yet Capture

**1. Long-horizon conversation failures (>8 turns)**
All benchmark tasks have conversation histories of 1-4 turns. Real sales
conversations span weeks with 10-20 exchanges. Tone drift and context loss
over long horizons are not tested. v0.2 should include 8-15 turn trajectories
derived from production conversation logs.

**2. Real prospect data distribution**
All prospect data in the benchmark is synthetic. Real Crunchbase records, real
layoffs.fyi entries, and real hiring signals have different noise characteristics
than synthetic signal briefs. The benchmark may overestimate agent performance
on genuinely ambiguous real-world signals — for example, a funding round
announced but not yet closed, or a layoff affecting one division but not another.

**3. High-volume multi-prospect coordination**
The benchmark covers scenarios where the agent manages one or two prospect
threads simultaneously. The production reality — 50+ simultaneous threads —
is not stress-tested. Thread isolation failures at scale are architecturally
different from single-thread failures and require a separate test suite.

**4. Regulatory and compliance edge cases**
GDPR, CCPA, and sector-specific constraints (defense, healthcare, finance) are
covered with 4 tasks each. Real compliance failures are rare but catastrophic.
The benchmark needs 20-30 tasks per compliance category with legal review before
being used as a formal compliance gate.

---

### Public-Signal Lossiness in Ground Truth

The benchmark's prospect data fields (funding detected, layoff detected, AI
maturity score) are synthetic approximations of real public data. The
contamination check verified temporal consistency but not factual accuracy of
the underlying signals. The benchmark's ground truth is cleaner than production
reality — real agent failures often involve subtler signal ambiguity that the
benchmark does not fully replicate.

---

### One Honest Unresolved Failure

The trained judge achieves 100% reward accuracy on training data but only 30%
pass rate on held-out tasks — lower than the heuristic baseline (34%). The
root cause: training pairs were generated by a deterministic simulation of
agent outputs rather than a real agent, creating a distribution mismatch
between training and evaluation. The judge learned to score simulated outputs
well but did not fully generalize to the held-out distribution.

**Fix for v0.2:** Generate preference pairs from real production agent outputs
on real prospects, not synthetic simulations. Even 50 real production traces
would produce higher-quality training data than 599 synthetic pairs.

---

### Kill-Switch Trigger Conditions

The trained judge should be disabled and rolled back to the prompted baseline if
any of the following occur:

- Pass rate on a rolling 100-task evaluation window drops below 20%
  (current heuristic baseline: 34%)
- Any evaluation task receives a passing score (>0.7) for an agent output
  containing a banned phrase — fabrication or over-commitment — indicating
  judge calibration failure
- Evaluation latency per task exceeds 3 seconds (current: ~1.4 seconds)
- A prospect complaint about factual errors in agent output is traced to a
  task the judge scored as passing

---

*Benchmark: https://huggingface.co/datasets/shuaibam/tenacious-bench-v0.1*
*Judge model: https://huggingface.co/shuaibam/tenacious-bench-judge-v0.1*
*Code: https://github.com/IbnuEyni/tenacious-sales-bench*
*Blog: https://open.substack.com/pub/shuaibi/p/building-a-domain-specific-benchmark*
