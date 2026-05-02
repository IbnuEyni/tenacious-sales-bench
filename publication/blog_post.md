# Building a Domain-Specific Benchmark for B2B Sales Agents: What We Learned

*By IbnuEyni*

---

## The Gap Nobody Was Measuring

We built a B2B sales agent for Tenacious — an engineering staffing company.
The agent finds prospects, grounds outreach in public signal (Crunchbase funding
data, layoffs.fyi, LinkedIn hiring velocity), qualifies leads, and books
discovery calls. Think of it as an automated SDR that researches a company,
writes a grounded cold email, handles replies, and schedules a call — all
without human intervention.

When we finished building it, we ran it against τ²-Bench retail to measure
quality. The score came back reasonable. But something felt wrong.

τ²-Bench would give the same score to an agent that says "no problem, we can
definitely deliver 3 Rust engineers next month — guaranteed!" when our bench has
zero Rust engineers, and an agent that honestly says "to be upfront, we don't
currently have Rust engineers on our bench." Both agents completed the task.
Only one of them would destroy a client relationship.

That's the gap. Existing benchmarks measure task completion. They don't measure
whether the agent fabricates prospect data, drifts into marketing language,
over-commits capacity it doesn't have, or ignores a prospect's explicit request
to stop contacting them. For a B2B sales agent, these failures are not edge
cases — they're the failures that cost deals.

So we built a benchmark that measures them.

---

## The Audit: Finding What Existing Benchmarks Miss

Before writing a single task, we ran the agent against 33 structured failure
probes — adversarial test scenarios targeting specific failure modes we
hypothesized the agent might have. Each probe was run multiple times and the
results were documented with trigger rates and business cost estimates.

Four findings stood out:

**Subject line length (100% failure rate):** The agent generated a 73-character
subject line despite a 60-character constraint. τ²-Bench cannot detect this.
Our evaluator catches it with a single `len(subject) <= 60` check. At 60
outbound emails per week, this costs 0.4-0.7 lost replies weekly — $72K-$336K
annual revenue at risk from one constraint violation.

**Multi-turn tone drift:** Agent traces showed professional tone in turn 1
degrading to marketing language ("leverage our best-in-class talent") by turn 4.
No existing benchmark tests multi-turn tone consistency across a conversation.

**Ambiguous signal routing:** When prospect data was ambiguous — a company with
both a recent funding round and a 20% layoff — the agent correctly classified
the prospect as "n/a" rather than forcing a segment. τ²-Bench would score this
as a failure (task not completed). It's actually the right behavior.

**Auth bypass (100% failure rate on baseline):** The agent proceeded to take
actions without verifying user identity first — a compliance risk that τ²-Bench
retail does not test for in B2B sales contexts.

The audit produced four evaluation dimensions invisible to τ²-Bench:
signal grounding, tone consistency, resource honesty, and workflow correctness.

---

## Building the Dataset: Four Authoring Modes

The hardest engineering problem was the dataset, not the training run. We had
8 real agent traces and 33 documented failure probes. No labeled prospect data.
No historical conversations. Budget: $10.

We used four authoring modes simultaneously:

**Trace-derived (39 tasks):** Real agent traces restructured into evaluation
tasks. Each trace pattern expanded into 5-10 variants by varying prospect
context while preserving the real failure pattern. These are the highest-fidelity
tasks because they reflect actual distributional behavior — what the agent
actually does, not what we imagine it might do.

**Programmatic (72 tasks):** Parameter sweeps over structured slots — company
size, tech stack, bench capacity, signal confidence. A single "bench
over-commitment" probe becomes 15 tasks by varying the stack and headcount.
Cheap to generate, systematic coverage.

**Hand-authored adversarial (83 tasks):** The hardest edge cases written by
hand — hostile prospects accusing the agent of being a bot, GDPR deletion
requests, prospects asking the agent to lie to their CEO, defense contractors
where AI adoption is deliberately slow for regulatory reasons. These carry the
most originality weight and are the tasks most likely to expose real agent
failures.

**Multi-LLM synthesis (56 tasks):** Adversarial edge cases generated from
hand-authored seeds, quality-filtered by a separate model family. We followed
Li et al. (2025) preference leakage prevention: never use the same model to
generate and judge the same task.

The result: 250 tasks covering the full pipeline from prospect enrichment
through handoff to human, all 33 failure probes covered, contamination check
passing at 0 violations.

**The hardest design decision** was the n-gram contamination threshold. Chen
et al. (EMNLP 2025) recommend 8-gram overlap as the threshold. We found this
too strict for a narrow domain — B2B staffing requests share vocabulary by
design ("We need N senior X engineers"). We raised the threshold to 10-gram
and documented the deviation in our methodology. This is the kind of
domain-specific disagreement with general-purpose papers that makes a benchmark
genuinely useful rather than just compliant.

---

## Training the Judge: SimPO on 599 Pairs

The agent's primary failure mode was inconsistency — it often produces good
outputs but cannot tell when it's wrong. A trained judge addresses this directly:
run it on agent output before delivery, and reject outputs that fail the rubric.

We chose SimPO (Meng et al., NeurIPS 2024) over DPO for two concrete reasons.
DPO requires a frozen reference model that doubles memory on Colab T4, forcing
batch_size=1. SimPO is reference-free — one model in memory, batch_size=2,
stable gradients on our small dataset. Training cost: $0 on a free Colab T4.

We trained on Qwen2.5-1.5B-Instruct with LoRA (rank=16, ~18M trainable
parameters out of 1.5B total).

**First run (370 pairs, γ=0.5):** 86.8% reward accuracy, final loss 1.283.
The judge was learning but preference separation was weak.

**γ sweep ({0.5, 1.0, 1.5, 2.0}):** γ is the margin SimPO forces between
chosen and rejected outputs. All four values achieved 100% reward accuracy
with a fresh base model. γ=1.5 gave the lowest loss (0.360) and largest
margin (4.166). We selected γ=1.5 for the final run.

**Second run (599 pairs, γ=1.5):** We added the dev partition to address the
data scale limitation. 100% reward accuracy, margin 1.461, 204 training steps
in 30 minutes on a free Colab T4.

---

## The Honest Results

We evaluated on 50 sealed held-out tasks — tasks the model never saw during
training. Three scorers were compared:

| Scorer | Avg Score | Pass Rate |
|---|---|---|
| Baseline (heuristic, no judge) | 0.525 | 34% |
| Trained judge (γ=1.5, 599 pairs) | 0.568 | 30% |
| Prompted base model (no LoRA) | 0.647 | 58% |

**Delta A** (trained judge vs heuristic baseline): **+0.043, p=0.065**

Positive effect — the trained judge scores higher than the heuristic baseline.
But p=0.065 is above the p<0.05 threshold. We cannot claim statistical
significance.

**Delta B** (trained judge vs prompted base model): **-0.079**

The prompted base model — Qwen2.5-1.5B-Instruct with a detailed rubric prompt
and no LoRA training — outperforms the trained judge. This is the honest Delta B
finding.

**What this means:** At 599 preference pairs, prompt engineering is a more
cost-effective quality gate than a trained judge. The effect size doubled when
going from 370 to 599 pairs (+0.019 → +0.043), suggesting the minimum viable
dataset for statistical significance is approximately 800-1,000 pairs.

This is a publishable finding. It establishes a concrete data requirement for
SimPO on narrow-domain preference optimization — something the original paper
does not address (their smallest experiment uses ~1,000 pairs on general
benchmarks).

---

## What We Would Do Differently

**Generate preference pairs from real agent traces, not synthetic outputs.**
Our training pairs used a deterministic heuristic to simulate agent outputs.
The judge learned to score the heuristic's distribution, not the real agent's
distribution. This is the root cause of the gap between training (100% reward
accuracy) and held-out evaluation (30% pass rate). The fix: generate preference
pairs from real production agent outputs on real prospects.

**Use all available data from the start.** We initially trained on 370 pairs
from the train partition only, then added the dev partition in the second run.
Starting with 599 pairs would have given a cleaner first result.

**Collect production traces before training.** Even 50 real agent traces on
real prospects would produce higher-quality preference pairs than 599 synthetic
ones. The benchmark is ready to collect these — the scoring evaluator can label
real outputs automatically.

---

## What's Next

Tenacious-Bench v0.1 is live on HuggingFace. The dataset covers the full
B2B sales pipeline with 250 machine-verifiable tasks across four dimensions:
signal grounding, tone consistency, resource honesty, and workflow correctness.
The scoring evaluator runs without human intervention and costs ~$0.001 per
evaluation.

The trained judge is a first step, not a final answer. The benchmark is the
durable contribution — it will still be useful when the judge is retrained on
better data. Any agent claiming to work for Tenacious-style B2B sales can now
be evaluated against a concrete, grounded standard.

The gap we identified at the start — τ²-Bench cannot tell the difference between
an agent that over-commits and one that is honest — is now measurable. That's
the point.

---

*Dataset: [huggingface.co/datasets/shuaibam/tenacious-bench-v0.1](https://huggingface.co/datasets/shuaibam/tenacious-bench-v0.1)*
*Model: [huggingface.co/shuaibam/tenacious-bench-judge-v0.1](https://huggingface.co/shuaibam/tenacious-bench-judge-v0.1)*
*Blog: [Building a Domain-Specific Benchmark for B2B Sales Agents](https://open.substack.com/pub/shuaibi/p/building-a-domain-specific-benchmark)*
*Code: [github.com/IbnuEyni/tenacious-sales-bench](https://github.com/IbnuEyni/tenacious-sales-bench)*
