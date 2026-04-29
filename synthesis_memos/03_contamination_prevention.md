# Synthesis Memo: Recent Advances in LLM Benchmarks against Data Contamination

**Paper:** Chen et al., EMNLP 2025
**Category:** Common (all paths)
**Date:** 2026-04-28

## Core Contribution

Chen et al. survey contamination-prevention techniques across three generations: static benchmarks (fixed test sets vulnerable to memorization), dynamic benchmarks (procedurally generated or time-shifted), and hybrid approaches. They recommend three minimum checks: n-gram overlap, embedding similarity, and temporal verification. They argue that static benchmarks are fundamentally broken for LLM evaluation because training data increasingly includes benchmark test sets.

## Key Design Choices Relevant to Tenacious-Bench

1. **N-gram overlap threshold** (Section 3.2): Less than 8-gram overlap between held-out and training partitions.
2. **Embedding similarity** (Section 3.3): Cosine similarity below 0.85 for any held-out/train pair.
3. **Time-shift verification** (Section 3.4): Tasks referencing real-world events must be from documentable time windows.
4. **Dynamic evaluation** (Section 4): Procedurally generated tasks resist memorization better than fixed test sets.

## Where I Disagree: 8-Gram Threshold Is Too Strict for Narrow-Domain Benchmarks

Chen et al.'s 8-gram threshold (Section 3.2, Table 4) is calibrated for general NLP benchmarks — MMLU, HellaSwag, ARC — where the input vocabulary spans all of natural language. In a narrow B2B sales domain, legitimate tasks *necessarily* share vocabulary.

**Evidence from our contamination check:**
- Running `contamination_check.py` on our current 41-task dataset flagged 2 held-out tasks for 8-gram overlap. The overlapping 8-gram: `"we need 10 senior ml engineers. can you"` and `"we need 15 senior python engineers. can you"`. These are *different tasks* testing different bench capacities (ML: 5 available vs Python: 12 available), but they share the prospect's request template.
- This is not contamination — it's domain vocabulary. Every B2B staffing request follows the pattern "We need N senior [LANGUAGE] engineers." An 8-gram window captures this template regardless of the actual test content (the bench state and expected honesty behavior).

**My position:** For narrow-domain benchmarks, the n-gram check should operate on the *discriminative content* (the fields that determine the correct answer), not the full input text. In our case, the discriminative content is `bench_state` + `expected_behavior`, not the prospect's message template. I propose a modified check: 8-gram overlap on `signal_brief` + `bench_state` + `expected_behavior` fields only, with a separate 4-gram check on `conversation_history` to catch verbatim message reuse.

Alternatively, the threshold could be relaxed to 12-grams for the full input, which would still catch genuine contamination (a held-out task copied verbatim into training) while allowing shared domain vocabulary.

**Evidence supporting this isn't just template noise:**
- Probe 3.1 (Rust, bench=0) and Probe 3.2 (Python, bench=7 of 15 requested) test fundamentally different failure modes — zero-capacity honesty vs. partial-capacity honesty. Flagging them as contaminated because the prospect uses similar phrasing would force us to artificially diversify surface text, reducing the benchmark's fidelity to real B2B conversations.

## What I Adopt

- All three checks implemented (`contamination_check.py`): n-gram, embedding similarity, time-shift.
- Embedding similarity at 0.85 threshold — this catches genuine semantic duplicates without the surface-vocabulary problem.
- Time-shift verification for any task referencing funding dates or hiring signals.
- Deterministic seed (42) for partitioning to ensure reproducibility.

**Design decision:** I implement the 8-gram check as specified for compliance, but document the false-positive rate in `contamination_check.json` and flag domain-vocabulary overlaps separately from genuine contamination. The held-out partition is sealed only after manual review of flagged pairs confirms they test different failure modes.
