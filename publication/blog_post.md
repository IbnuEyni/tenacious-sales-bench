# Building a Domain-Specific Benchmark for B2B Sales Agents: What We Learned

*By IbnuEyni | TRP1 Week 11*

---

## The Gap Nobody Was Measuring

When we finished building the Tenacious Conversion Engine in Week 10 — a B2B
sales agent that finds prospects, grounds outreach in public signal, qualifies
leads, and books discovery calls — we ran it against τ²-Bench retail to measure
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

## The Audit: What Week 10 Evidence Proved

Before writing a single task, we audited what the existing benchmarks miss using
real evidence from Week 10.

**Probe 4.5** showed a 100% failure rate on subject line length — the agent
generated a 73-character subject line despite a 60-character constraint. τ²-Bench
cannot detect this. Our evaluator catches it with a single `len(subject) <= 60`
check. At 60 outbound emails per week, this costs 0.4-0.7 lost replies weekly —
$72K-$336K annual revenue at risk from one constraint violation.

**Traces `llm_gap_analysis_7a52cdcf_3` through `_7`** showed professional tone
in turn 1 degrading to marketing language by turn 4. No existing benchmark tests
multi-turn tone consistency. We built 8 tasks specifically from this trace
pattern.

**Trace `out_enrichment_complete_c0033ad8_4`** showed the agent correctly
classifying a prospect as "n/a" when signals were ambiguous — honest behavior
that τ²-Bench would score as a failure (task not completed). We built 8 tasks
testing this ambiguous-signal routing.

The audit produced four evaluation dimensions invisible to τ²-Bench:
signal grounding, tone consistency, resource honesty, and workflow correctness.

---

## Building the Dataset: Four Authoring Modes

The hardest engineering problem of the week was the dataset, not the training
run. We had 8 real traces and 33 documented failure probes. No labeled prospect
data. No historical conversations.

We used four authoring modes simultaneously:

**Trace-derived (39 tasks):** Real Week 10 traces restructured into evaluation
tasks. Each trace pattern expanded into 5-10 variants by varying prospect
context while preserving the real failure pattern. These are the highest-fidelity
tasks because they reflect actual distributional behavior.

**Programmatic (72 tasks):** Parameter sweeps over structured slots — company
size, tech stack, bench capacity, signal confidence. A single "bench
over-commitment" probe becomes 15 tasks by varying the stack and headcount.
Cheap to generate, systematic coverage.

**Hand-authored adversarial (83 tasks):** The hardest edge cases written by
hand — hostile prospects accusing the agent of being a bot, GDPR deletion
requests, prospects asking the agent to lie to their CEO, regulatory sectors
where AI adoption is deliberately slow. These carry the most originality weight
and are the tasks most likely to expose real agent failures.

**Multi-LLM synthesis (56 tasks):** Adversarial edge cases generated from
hand-authored seeds, quality-filtered by a separate model family. We followed
Li et al. (2025) preference leakage prevention: never use the same model to
generate and judge the same task.

The result: 250 tasks covering the full pipeline from enrichment through
handoff, all 33 Week 10 probes covered, contamination check passing at 0
violations.

**The hardest design decision** was the n-gram contamination threshold. Chen
et al. (EMNLP 2025) recommend 8-gram overlap as the threshold. We found this
too strict for a narrow domain — B2B staffing requests share vocabulary by
design ("We need N senior X engineers"). We raised the threshold to 10-gram
and documented the deviation in our methodology. This is the kind of
domain-specific disagreement with general-purpose papers that makes a benchmark
genuinely useful rather than just compliant.

---

## Training the Judge: SimPO on 599 Pairs

We chose Path B — training a preference judge rather than a generation component.
The evidence pointed clearly to inconsistency failures, not generation quality
failures. The agent often produces good outputs but cannot tell when it's wrong.
A trained judge addresses this directly.

We chose SimPO (Meng et al., NeurIPS 2024) over DPO for two concrete reasons:
DPO requires a frozen reference model that doubles memory on Colab T4, forcing
batch_size=1. SimPO is reference-free — one model in memory, batch_size=2,
stable gradients on our small dataset.

**First run (370 pairs, γ=0.5):** 86.8% reward accuracy, final loss 1.283.
The judge was learning but preference separation was weak.

**γ sweep ({0.5, 1.0, 1.5, 2.0}):** All four values achieved 100% reward
accuracy with a fresh base model. γ=1.5 gave the lowest loss (0.360) and
largest margin (4.166). We selected γ=1.5 for the final run.

**Second run (599 pairs, γ=1.5):** We added the dev partition (74 tasks →
~220 more pairs) to address the data scale limitation. 100% reward accuracy,
margin 1.461, 204 training steps in 30 minutes on a free Colab T4.

---

## The Honest Results

Delta A (trained judge vs heuristic baseline): **+0.043, p=0.065**

Positive effect — the trained judge scores higher than the heuristic baseline.
But p=0.065 is above the p<0.05 threshold. We cannot claim statistical
significance.

Delta B (trained judge vs prompted base model): **-0.079**

The prompted base model (Qwen2.5-1.5B-Instruct with a detailed rubric prompt,
no LoRA) outperforms the trained judge. This is the honest Delta B finding that
the challenge spec says to report even when negative.

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
distribution. This is the root cause of the distribution mismatch between
training (100% accuracy) and held-out evaluation (30% pass rate).

**Use the dev partition from the start.** We initially trained on 370 pairs
(train partition only) and only added the dev partition in the second run.
Starting with 599 pairs would have given us a cleaner first result.

**Collect production traces before training.** The highest-value training data
would come from real agent outputs on real prospects — not synthetic simulations.
Even 50 real traces would produce higher-quality preference pairs than 599
synthetic ones.

---

## What's Next

Tenacious-Bench v0.1 is live on HuggingFace. The dataset covers the full
B2B sales pipeline with 250 machine-verifiable tasks. The scoring evaluator
runs without human intervention.

The trained judge is a first step, not a final answer. The benchmark is the
durable contribution — it will still be useful when the judge is retrained on
better data. Any agent claiming to work for Tenacious-style B2B sales can now
be evaluated against a concrete, grounded standard.

The gap we identified at the start — τ²-Bench cannot tell the difference between
an agent that over-commits and one that is honest — is now measurable. That's
the point.

---

*Dataset: [huggingface.co/datasets/shuaibam/tenacious-bench-v0.1](https://huggingface.co/datasets/shuaibam/tenacious-bench-v0.1)*
*Model: [huggingface.co/shuaibam/tenacious-bench-judge-v2-599pairs](https://huggingface.co/shuaibam/tenacious-bench-judge-v2-599pairs)*
*Code: [github.com/IbnuEyni/tenacious-sales-bench](https://github.com/IbnuEyni/tenacious-sales-bench)*
