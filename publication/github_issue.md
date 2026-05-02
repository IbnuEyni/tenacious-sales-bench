# τ²-Bench Gap for B2B Sales Agents — Tenacious-Bench v0.1

**Issue type:** Gap finding + complementary dataset contribution

---

## Background

We built a B2B sales agent for Tenacious, an engineering staffing company.
The agent automates the full outreach pipeline: it enriches prospect data from
public sources (Crunchbase, layoffs.fyi, LinkedIn hiring signals), classifies
prospects by segment, writes grounded cold emails, handles prospect replies,
and books discovery calls.

When we evaluated it against τ²-Bench retail, the scores looked reasonable.
But τ²-Bench was measuring the wrong things for our use case.

---

## The Gap

τ²-Bench retail evaluates task completion in retail customer service scenarios.
For B2B sales agents, the critical failure modes are different and invisible
to τ²-Bench:

**1. Signal Grounding**
Does the agent fabricate claims about prospect funding, layoffs, or AI maturity?
τ²-Bench has no mechanism to verify whether agent claims are grounded in
provided data vs invented. In B2B sales, one fabricated claim ("you recently
raised a Series A") to a company that never raised destroys the relationship
permanently.

**2. Tone Consistency**
Does the agent maintain professional tone across multi-turn conversations?
τ²-Bench measures task completion, not style guide adherence across turns.
We observed the agent drifting from professional language in turn 1 to
marketing clichés ("leverage our best-in-class talent") by turn 4.

**3. Resource Honesty**
Does the agent over-commit when capacity doesn't match prospect needs?
An agent saying "guaranteed delivery of 3 Rust engineers" when the bench has
zero Rust engineers completes the task but destroys the client relationship.
τ²-Bench scores both responses identically.

**4. Workflow Correctness**
Does the agent follow B2B sales sequences, respect decision-maker hierarchies,
and handle legal/compliance requests (GDPR, CCPA) correctly? These are
domain-specific workflow requirements that retail benchmarks don't test.

---

## Evidence

We ran 33 structured failure probes against the agent and documented the results:

- **Subject line length:** 100% failure rate — agent generated 73-char subject
  despite a 60-char constraint. τ²-Bench cannot detect this. At 60 outbound
  emails/week, this costs $72K-$336K annual revenue.
- **Auth bypass:** 100% failure rate on baseline — agent proceeded without
  verifying user identity, a compliance risk τ²-Bench retail does not test.
- **Reasoning loops:** 20% failure rate on τ²-Bench held-out — agent hit
  max-steps limit without completing the task.
- **Timezone handling:** 50% failure rate — agent proposed meeting times
  without explicit timezone labels across a 10-hour offset.

Aggregate trigger rate across 19 tested probes: **16%** — meaning 1 in 6
agent interactions had a measurable failure that τ²-Bench would not catch.

---

## What We Built

**Tenacious-Bench v0.1** — 250 machine-verifiable evaluation tasks covering:

- Full B2B sales pipeline: enrichment → ICP classification → outreach →
  engagement → booking → handoff
- 4 evaluation categories: workflow_correctness (112), resource_honesty (52),
  signal_grounding (44), tone_consistency (42)
- Hybrid scoring: regex for hard constraints (subject length, banned phrases,
  fabrication detection) + LLM judge for semantic dimensions
- Contamination check: PASSED — 0 violations (10-gram + Jaccard + time-shift)
- Partitions: train=126, dev=74, held-out=50 (sealed)

**Trained judge:** SimPO-trained Qwen2.5-1.5B-Instruct LoRA adapter
- 599 preference pairs, γ=1.5, 100% reward accuracy on training data
- Delta A: +0.043, p=0.065 (approaching but not reaching significance)
- Honest finding: prompted base model outperforms trained judge at this
  data scale — minimum viable dataset estimated at ~800-1,000 pairs

---

## Links

- Dataset: https://huggingface.co/datasets/shuaibam/tenacious-bench-v0.1
- Model: https://huggingface.co/shuaibam/tenacious-bench-judge-v0.1
- Code: https://github.com/IbnuEyni/tenacious-sales-bench
- Blog post: https://open.substack.com/pub/shuaibi/p/building-a-domain-specific-benchmark

---

## Question for the Community

Has anyone else encountered these gaps when applying τ²-Bench to non-retail
agent workflows? We'd be interested in:

1. Whether the four dimensions we identified (signal grounding, tone
   consistency, resource honesty, workflow correctness) generalize to other
   B2B domains — legal, finance, healthcare sales
2. Whether domain-specific benchmarks are the right approach for each vertical,
   or whether τ²-Bench could be extended with domain-specific rubrics
3. Whether the contamination prevention approach (10-gram threshold relaxed
   from the standard 8-gram for narrow-domain vocabulary) is the right
   tradeoff

Happy to discuss methodology, share the contamination check scripts, or
collaborate on extending coverage to other sales workflows.
