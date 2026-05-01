# GitHub Issue: τ²-Bench Gap for B2B Sales Agents — Tenacious-Bench v0.1

**Repository:** tau-bench (or AgentBench)
**Issue type:** Gap finding + complementary dataset contribution

---

## Summary

We identified four evaluation dimensions critical for B2B sales agents that
τ²-Bench retail cannot grade, and built a domain-specific benchmark to fill
the gap. Sharing here for community awareness and to invite feedback.

## The Gap

τ²-Bench retail evaluates task completion in retail customer service scenarios.
For B2B sales agents, the critical failure modes are different:

**1. Signal Grounding** — Does the agent fabricate claims about prospect
funding, layoffs, or AI maturity? τ²-Bench has no mechanism to verify whether
agent claims are grounded in provided data vs invented.

**2. Tone Consistency** — Does the agent maintain professional tone across
multi-turn conversations? τ²-Bench measures task completion, not style guide
adherence across turns.

**3. Resource Honesty** — Does the agent over-commit when capacity doesn't
match prospect needs? An agent saying "guaranteed delivery" when bench has
zero engineers completes the task but destroys the client relationship.

**4. Workflow Correctness** — Does the agent follow B2B sales sequences,
respect decision-maker hierarchies, and handle legal/compliance requests
(GDPR, CCPA) correctly?

## Evidence

From Week 10 Tenacious Conversion Engine analysis:
- Probe 4.5: 100% failure rate on subject line length (73 chars vs 60 limit)
- Probe 7.1: 100% auth bypass on baseline
- Probe 6.2: 20% max-steps failures on τ²-Bench held-out
- 16% aggregate trigger rate across 19 tested probes
- $72K-$336K annual revenue at risk from tone failures alone

## What We Built

**Tenacious-Bench v0.1** — 250 machine-verifiable tasks covering:
- Full B2B sales pipeline (enrichment → classification → outreach → engagement → booking → handoff)
- All 33 documented failure probes
- 4 evaluation categories with hybrid regex + LLM judge scoring
- Contamination check: PASSED (0 violations)
- Partitions: train=126, dev=74, held-out=50 (sealed)

**Trained judge:** SimPO-trained Qwen2.5-1.5B-Instruct LoRA adapter
- 599 preference pairs, γ=1.5
- Delta A: +0.043, p=0.065 (approaching significance)
- Honest finding: prompted base model outperforms trained judge at this data scale

## Links

- Dataset: https://huggingface.co/datasets/shuaibam/tenacious-bench-v0.1
- Model: https://huggingface.co/shuaibam/tenacious-bench-judge-v2-599pairs
- Code: https://github.com/IbnuEyni/tenacious-sales-bench
- Blog post: [link]

## Question for the Community

Has anyone else encountered these gaps when applying τ²-Bench to non-retail
agent workflows? We'd be interested in whether the benchmark generalizes to
other B2B domains (legal, finance, healthcare sales) or whether domain-specific
benchmarks are the right approach for each vertical.

Happy to discuss methodology, share the contamination check scripts, or
collaborate on extending coverage to other sales workflows.
