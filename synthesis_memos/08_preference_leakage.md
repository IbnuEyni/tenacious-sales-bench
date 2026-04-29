# Synthesis Memo: Preference Leakage — A Contamination Problem in LLM-as-a-Judge

**Paper:** Li et al., 2025
**Category:** Path B — preference-tuned judge
**Date:** 2026-04-28

## Core Contribution

Li et al. identify and quantify *preference leakage*: when the same LLM (or same model family) generates candidate outputs and then judges them, the judge systematically prefers outputs from its own family. This isn't a bug in the judge — it's a statistical artifact. Models from the same family share distributional biases (token preferences, phrasing patterns, reasoning structures), and the judge recognizes these as "higher quality" because they match its own implicit quality prior.

Key findings (Section 3, Table 1): GPT-4 judges prefer GPT-4-generated text over Claude-generated text by 12-18% even when human annotators rate them equally. The effect is strongest for stylistic dimensions (tone, fluency) and weakest for factual dimensions (correctness, grounding).

## Key Design Choices Relevant to Tenacious-Bench

1. **Model-family rotation** (Section 4.1): Never use the same model family to generate and judge the same data point.
2. **Prompt-level decontamination** (Section 4.2): Vary prompt templates between generation and judging to reduce surface-pattern matching.
3. **Cross-family calibration** (Section 4.3): Measure judge agreement across model families on a calibration set before trusting scores.

## Where I Disagree: Model-Family Rotation May Be Insufficient for Narrow Domains

Li et al.'s mitigation — rotate model families between generation and judging — is necessary but may not be sufficient for Tenacious-Bench. Their experiments (Section 3) are on general-purpose text where model families have distinct stylistic signatures. In our narrow B2B sales domain, the stylistic space is much smaller.

**Evidence from Week 10:**

Our pipeline has three LLM touchpoints:
1. **Task generation** (multi-LLM synthesis): Claude/GPT for hard seeds, Qwen3-Next for bulk variations.
2. **Quality filtering** (judge): A separate model scores generated tasks for inclusion.
3. **Preference pair construction** (corrections): A model rewrites failed outputs into "chosen" examples.

Li et al. would say: use different families for steps 1, 2, and 3. We do this — GPT for corrections (step 3), Qwen for judging (step 2). But here's the problem:

Trace `out_email_send_c0033ad8_5` shows a real agent output with subject line "Request: Exploring technical SEO partnerships post-restructuring" — 73 characters, failing the 60-char constraint. When we ask *any* LLM to "rewrite this to be under 60 characters," the rewrite will reflect that LLM's compression style. If the judge is from a different family, it might penalize the compression style rather than evaluating the constraint satisfaction.

**Specific concern:** For our resource_honesty dimension, the "chosen" output must acknowledge a bench gap. If GPT writes the acknowledgment as "We don't currently have Rust engineers on our bench" and Qwen judges it, Qwen might score it lower than a Qwen-style acknowledgment — not because it's worse, but because of distributional mismatch. This is *reverse* preference leakage: the judge penalizes outputs from other families.

**My position:** Model-family rotation addresses *self-preference* leakage but introduces *cross-family penalty* leakage. For our narrow domain, I add a fourth mitigation beyond Li et al.'s three:

4. **Constraint-anchored judging**: For dimensions with hard constraints (subject length ≤60, no banned phrases, bench capacity stated), use deterministic checks instead of LLM judges. Preference leakage cannot affect a regex match. Reserve LLM judges only for dimensions where semantic understanding is required (resource_honesty, workflow_correctness), and anchor those judges with explicit rubric criteria that reference the task's `expected_behavior` fields rather than asking for open-ended quality assessment.

This reduces the surface area where preference leakage can operate from 4 dimensions to 2.

## What I Adopt

- **Model-family rotation** as a hard rule: generation and judging never use the same model family. Documented in `methodology.md`.
- **Cross-family calibration**: Before trusting the judge on the full dataset, score 50 tasks with both the dev-tier and eval-tier judges and measure correlation. If correlation <0.8, adjust judge prompts.
- **Prompt variation**: Different prompt templates for generation vs. judging, even when using different models, to reduce surface-pattern matching.
- **Rotation policy documentation**: Every task's `metadata` records which model generated it and which model judged it, enabling post-hoc leakage analysis.
