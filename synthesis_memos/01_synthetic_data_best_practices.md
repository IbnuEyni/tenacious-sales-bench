# Synthesis Memo: Best Practices and Lessons Learned on Synthetic Data for Language Models

**Paper:** Liu et al., COLM 2024
**Category:** Common (all paths)
**Date:** 2026-04-28

## Core Contribution

Liu et al. survey synthetic data practices across the LLM lifecycle — pretraining, fine-tuning, and evaluation. Their central recommendation (Section 4.2): synthetic data quality dominates quantity, and multi-stage filtering pipelines are essential. They propose a taxonomy of failure modes: distribution collapse, hallucination amplification, and evaluation contamination.

## Key Design Choices Relevant to Tenacious-Bench

1. **Quality filtering before quantity scaling** (Section 4.2, Recommendation 3): Use LLM-as-a-judge to filter generated data, with pointwise scoring on coherence and verifiability.
2. **Multi-model generation** (Section 3.3): Route generation across model families to avoid monoculture in synthetic outputs.
3. **Seed corpus amplification** (Section 3.1): Small high-quality seeds can be expanded 10-50x through template variation and paraphrase.

## Where I Disagree: Seed Corpus Size Assumptions

Liu et al. assume a "small" seed corpus of 500-5,000 examples (Section 3.1, Table 2). Their amplification ratios (10-50x) are calibrated against this range. Tenacious-Bench starts from a fundamentally smaller base: 8 trace samples and 33 probe definitions — roughly two orders of magnitude below their assumed floor.

**Evidence from Week 10:**
- `trace_samples.jsonl` contains 8 entries. Even with aggressive restructuring (each trace → 5-10 task variants), trace-derived tasks cap at ~80.
- The probe library has 33 probes, but only 19 were tested and only 4 triggered failures (Probes 4.5, 6.2, 7.1, 8.1). The untested probes (14 of 33) have no empirical grounding — expanding them risks fabricating failure patterns that don't exist in the real system.
- Trace `llm_gap_analysis_1d816fd2_2` (7,314 tokens, 4x normal) is a genuine cost pathology example, but it's a single data point. Amplifying it 10x produces 10 tasks that all test the same narrow failure.

**My position:** At our seed size, Liu et al.'s amplification strategy produces *coverage illusion* — many tasks that look diverse but test the same 4 failure modes. The programmatic sweep approach (combinatorial expansion over structured parameters) is more honest about coverage than paraphrase-based amplification, because the parameter axes (company size, tech stack, bench capacity) are independently meaningful even when the underlying failure mode is the same.

**Design decision:** I weight programmatic generation (30%) and hand-authored adversarial (15%) higher than Liu et al. would recommend for our scale, and weight multi-LLM synthesis (25%) lower. The synthesis budget goes to genuinely novel scenarios (untested probes, multi-turn edge cases) rather than bulk paraphrase of existing traces.

## What I Adopt

- Multi-model routing for synthesis (Section 3.3) — different model families for generation vs. judging, directly addressing preference leakage.
- Pointwise quality filtering with documented thresholds (Section 4.2) — every generated task scored on input coherence, ground-truth verifiability, and rubric clarity before inclusion.
- Explicit documentation of synthetic-to-real ratio per partition (Section 5.1) — the `source_mode` field in our schema tracks this.
