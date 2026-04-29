# Synthesis Memo: A Survey on LLM-as-a-Judge

**Paper:** Gu et al., 2024–2025 (latest revision)
**Category:** Common (all paths)
**Date:** 2026-04-28

## Core Contribution

Gu et al. comprehensively survey the LLM-as-a-Judge paradigm: pointwise scoring (rate a single output), pairwise comparison (pick the better of two), and reference-guided evaluation. They document systematic biases — position bias, verbosity bias, self-enhancement bias — and propose mitigation strategies including multi-judge ensembles, calibration protocols, and rubric-anchored prompting.

## Key Design Choices Relevant to Tenacious-Bench

1. **Pointwise vs. pairwise** (Section 3): Pointwise for absolute quality scoring; pairwise for preference-pair construction in training data.
2. **Rubric-anchored prompting** (Section 4.2): Providing explicit scoring criteria reduces judge variance by 15-30%.
3. **Multi-judge ensembles** (Section 5.1): Using 2-3 judges and taking majority vote improves reliability.
4. **Position bias mitigation** (Section 4.3): Randomize candidate order in pairwise comparisons.

## Where I Disagree: The Survey Undervalues Deterministic Checks for Constrained Domains

Gu et al. frame LLM-as-a-Judge as the primary evaluation mechanism, with deterministic checks (regex, rule-based) mentioned only as "baseline" approaches (Section 2.1, one paragraph). Their implicit recommendation is to use LLM judges for all evaluation dimensions.

For Tenacious-Bench, this is wrong for at least two of our four scoring dimensions.

**Evidence from Week 10:**

*Dimension 1 — Tone adherence (subject length):* Probe 4.5 showed 100% failure rate on a binary constraint: subject line ≤60 characters. An LLM judge adds zero value here. `len(subject) <= 60` is deterministic, instant, free, and perfectly reliable. The LLM judge would introduce variance on a question that has no ambiguity.

*Dimension 2 — Signal accuracy (fabrication detection):* Probe 2.3 tests whether the agent fabricates funding claims for companies not in Crunchbase. The check is: does the output contain any of the banned phrases ("you recently raised", "your Series A") when `funding_detected: false`? This is a regex match against a known phrase list. An LLM judge might *miss* a subtle fabrication or *hallucinate* one that isn't there.

*Dimension 3 — Resource honesty:* This is where LLM judges earn their keep. Probe 3.1 asks whether the agent "acknowledges" a capacity gap — but acknowledgment can take many forms ("we don't have Rust engineers", "Rust isn't our strength currently", "I'd want to be upfront that our bench is stronger in Python"). No finite regex list captures all valid honesty expressions. An LLM judge with rubric-anchored prompting is the right tool.

*Dimension 4 — Workflow correctness:* Similarly requires LLM judgment — "did the agent qualify before booking?" has too many valid surface forms for regex.

**My position:** The optimal scoring evaluator is a *hybrid* — deterministic checks for dimensions with hard constraints (tone_adherence, signal_accuracy), LLM judges for dimensions requiring semantic understanding (resource_honesty, workflow_correctness). Our schema's `verification_method` field (regex | llm_judge | schema_check) encodes this per-dimension, which is more principled than the survey's implicit "use LLM judges for everything" stance.

**Cost evidence:** At our scale (250 tasks × 4 dimensions), using an LLM judge for all dimensions would cost ~$0.50-1.00 per evaluation pass. Using regex for 2 dimensions and LLM for 2 cuts this to ~$0.25-0.50 — meaningful when the total eval budget is $2-3.

## What I Adopt

- Rubric-anchored prompting for all LLM judge calls — the `criteria` field in our scoring rubric is passed directly to the judge prompt.
- Pointwise scoring (1-5 scale) for quality filtering during dataset authoring.
- Pairwise comparison for constructing preference pairs in Path B training data.
- Model-family rotation between generator and judge to prevent self-enhancement bias.
