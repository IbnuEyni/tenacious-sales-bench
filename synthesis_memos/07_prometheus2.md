# Synthesis Memo: Prometheus 2 — An Open-Source Language Model Specialized in Evaluating Other Language Models

**Paper:** Kim et al., 2024
**Category:** Path B — preference-tuned judge
**Date:** 2026-04-28

## Core Contribution

Prometheus 2 trains a 7B-parameter open judge model that approaches GPT-4-level evaluation quality on both pointwise scoring and pairwise comparison tasks. Key innovations: (1) merging pointwise and pairwise evaluation into a unified training format, (2) training on diverse rubrics rather than a single scoring scheme, and (3) using weight merging of separately trained pointwise and pairwise models to get the best of both.

## Key Design Choices Relevant to Tenacious-Bench

1. **Unified evaluation format** (Section 3.1): A single model handles both "score this output 1-5" and "which of these two outputs is better" — useful because we need pointwise scoring for the evaluator and pairwise comparison for preference-pair construction.
2. **Rubric diversity in training** (Section 3.2): Training on 1,000+ different rubrics makes the judge generalizable. Each rubric is provided in the prompt, not baked into the model.
3. **Weight merging** (Section 3.3): Train two specialists (pointwise, pairwise), then merge weights. Outperforms training a single model on both tasks.
4. **Scale** (Section 4): 7B parameters, trained on 200K+ evaluation examples.

## Where I Disagree: Generality vs. Specialization at 2B Scale

Prometheus 2's core bet is *generality* — train on diverse rubrics so the judge works across domains. At 7B parameters with 200K training examples, this works. At our scale (Qwen 3.5 2B, ~1,500 preference pairs), I argue the opposite strategy is correct: *specialize aggressively*.

**Evidence from Week 10:**

Our judge needs to evaluate exactly 4 dimensions:
1. **Signal accuracy**: Did the agent fabricate claims? (Probe 2.3 — binary, regex-checkable for most cases)
2. **Tone adherence**: Subject length, banned phrases, interrogative phrasing? (Probe 4.5 — partially regex, partially semantic)
3. **Resource honesty**: Did the agent acknowledge capacity gaps? (Probe 3.1 — semantic, many valid surface forms)
4. **Workflow correctness**: Did the agent qualify before booking? (Probe 7.2 — semantic, multi-step reasoning)

Prometheus 2 trains on rubrics spanning code quality, creative writing, factual accuracy, safety, and more. A 2B model cannot absorb this breadth — it would learn shallow heuristics across many domains rather than deep judgment on our four dimensions.

**Specific disagreement with Section 3.2:** Kim et al. argue that rubric diversity during training improves generalization even to unseen rubrics. At 7B, yes — the model has capacity to learn meta-evaluation skills. At 2B, I expect rubric diversity to *hurt* because the model conflates unrelated evaluation criteria. A 2B judge trained exclusively on "does this B2B email acknowledge a bench capacity gap?" will outperform one trained on 1,000 rubrics including "is this Python code well-documented?"

**My design decision:** Train the judge on our 4 Tenacious-specific dimensions only. Each preference pair is tagged with its dimension, and the rubric criteria from our schema is included in the training prompt. This is the opposite of Prometheus 2's approach but appropriate for our parameter budget.

## What I Adopt

- **Rubric-in-prompt design** (Section 3.1): The scoring criteria is passed as part of the input, not hardcoded. This means the same judge model can evaluate different dimensions by changing the prompt — we get some flexibility without training on diverse rubrics.
- **Pointwise + pairwise capability**: We need pointwise for the production evaluator and pairwise for training data construction. Rather than weight merging (which requires training two models), we include both formats in our single training run.
- **Evaluation protocol** (Section 4.2): Their correlation-with-human-judgment methodology informs our inter-rater agreement check — we measure whether the trained judge agrees with our hand-labels on the 30-task subset.
