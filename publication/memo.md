# Memo: Tenacious-Bench v0.1 — Evaluation Results and Deployment Recommendation

**To:** Tenacious CEO and CFO
**From:** IbnuEyni, TRP1 Week 11
**Date:** 2026-04-30
**Re:** B2B Sales Agent Evaluation Benchmark — Results and Production Recommendation

---

## Page 1 — The Decision

### Executive Summary

We built a domain-specific evaluation benchmark (Tenacious-Bench v0.1) for the
Tenacious Conversion Engine and trained a preference judge to score agent outputs
automatically. The benchmark covers 250 tasks across the full sales pipeline —
enrichment through handoff — grounded in 33 documented failure modes from Week 10.

The trained judge shows a positive improvement over the heuristic baseline
(Delta A: +0.043 average score improvement) but this improvement does not yet
reach statistical significance (p=0.065, threshold p<0.05). Prompt engineering
alone outperforms the trained judge at this data scale (Delta B: -0.079).

### Headline Numbers

| Metric | Value |
|---|---|
| Benchmark tasks | 250 (100% valid, contamination PASSED) |
| Probes covered | 33/33 from Week 10 failure analysis |
| Baseline pass rate (no judge) | 34.0% |
| Trained judge pass rate | 30.0% |
| Prompted base model pass rate | 58.0% |
| Delta A (trained vs baseline) | +0.043, p=0.065 |
| Delta B (trained vs prompted) | -0.079 |
| Training cost | $0.00 (Colab T4, free tier) |
| Total budget spent | $0.15 of $10.00 |
| Training time | 30 min |

### Deployment Recommendation: DO NOT DEPLOY YET

**Rationale:** The trained judge improves over the heuristic baseline (+0.043)
but the improvement is not statistically significant. More importantly, a
well-prompted version of the same base model (Qwen2.5-1.5B-Instruct) achieves
58% pass rate without any training — outperforming the trained judge (30%).

**What this means in practice:** At current data scale (599 preference pairs),
prompt engineering is a more cost-effective quality gate than a trained judge.
The benchmark itself is production-ready and should be deployed immediately as
the evaluation standard. The trained judge component needs more data before
replacing the prompted baseline.

### What Should Change in Production

1. **Deploy the benchmark now** — use Tenacious-Bench v0.1 as the evaluation
   standard for all agent outputs. The scoring evaluator (regex + prompted judge)
   is ready and costs ~$0.001 per evaluation.

2. **Use the prompted judge as interim quality gate** — Qwen2.5-1.5B-Instruct
   with the rubric prompt achieves 58% pass rate. Deploy this as a rejection
   sampling layer while training data is collected.

3. **Collect 400 more preference pairs** — the effect size doubled when going
   from 370 to 599 pairs. Extrapolating, ~800-1,000 pairs should achieve
   statistical significance. These can be generated from production agent traces
   at zero additional cost.

4. **Retrain at 1,000 pairs** — expected to achieve p<0.05 on Delta A based on
   the observed scaling trend. Estimated training cost: $0 (Colab T4).

---

## Page 2 — The Skeptic's Appendix

### Four Failure Modes Tenacious-Bench v0.1 Does Not Capture

**1. Multi-turn trajectory failures (>8 turns)**
All tasks have conversation histories of 1-4 turns. Real sales conversations
can span weeks with 10-20 exchanges. Tone drift and context loss over long
horizons are not tested. v0.2 should include 8-15 turn trajectories derived
from production logs.

**2. Real prospect data distribution**
All prospect data is synthetic. Real Crunchbase records, real layoffs.fyi
entries, and real hiring signals have different noise characteristics than our
synthetic signal briefs. The benchmark may overestimate agent performance on
genuinely ambiguous real-world signals.

**3. Multi-company coordination**
Probes 5.1 and 5.2 (multi-thread leakage) are covered with only 2 tasks each.
The scenario where the agent manages 50+ simultaneous prospect threads — the
production reality — is not stress-tested. Thread isolation failures at scale
are architecturally different from single-thread failures.

**4. Regulatory and compliance edge cases**
GDPR, CCPA, and sector-specific constraints (defense, healthcare, finance) are
covered with 4 tasks each. Real compliance failures are rare but catastrophic.
The benchmark needs 20-30 tasks per compliance category with legal review before
being used as a compliance gate.

### Public-Signal Lossiness in Ground Truth

The signal_brief fields (funding_detected, layoff_detected, ai_maturity_score)
are synthetic approximations of real Crunchbase and layoffs.fyi data. The
contamination check verified temporal consistency but not factual accuracy of
the underlying signals. Tasks referencing "$20M Series B" use a placeholder —
real agent failures often involve subtler signal ambiguity (e.g., a funding
round announced but not yet closed, or a layoff affecting one division but not
another). The benchmark's ground truth is cleaner than production reality.

### One Honest Unresolved Failure

The trained judge (γ=1.5, 599 pairs) achieves 100% reward accuracy on training
data but only 30% pass rate on held-out tasks — lower than the heuristic
baseline (34%). This suggests the judge learned to score the training
distribution well but did not generalize to the held-out distribution. The root
cause is likely that the training pairs were generated by a deterministic
heuristic (`generate_agent_output()`) rather than a real agent, creating a
distribution mismatch between training and evaluation. v0.2 should generate
preference pairs from real production agent traces, not synthetic outputs.

### Kill-Switch Trigger Condition

The trained judge should be disabled and rolled back to the prompted baseline if:

- Pass rate on a rolling 100-task window drops below 20% (current baseline: 34%)
- Any held-out task receives a score >0.7 for an output containing a banned
  phrase (fabrication or over-commitment) — indicates judge calibration failure
- Latency per evaluation exceeds 3 seconds (current: ~1.4s on T4)
- A prospect complaint about factual errors in agent output is traced to a task
  the judge scored as passing
