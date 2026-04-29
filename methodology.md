# Methodology: Tenacious-Bench Construction and Training Path

## Path Selection: Path B - DPO Judge/Critic

**Justification from Week 10 Evidence:**

Based on analysis of trace IDs and probe results, the primary failure mode is **inconsistency** rather than generation quality:

1. **Trace Evidence**: 
   - `llm_gap_analysis_7a52cdcf_3` (turn 1, 770 output tokens, metadata: "initial professional tone") vs `llm_gap_analysis_7a52cdcf_7` (turn 4, 701 output tokens, metadata: "potential tone drift — evidence for Probe 4.1") — same prospect, same model, qualitatively different output character across turns.
   - `llm_ai_maturity_c0033ad8_3` vs `llm_ai_maturity_850154ee_1`: identical input token count (424) but different output tokens (400 vs 453) and different latency (6.2s vs 7.8s) for the same ai_maturity scoring step. The metadata on both explicitly flags "confidence variation" and "inconsistency" — the model is not deterministic on a task that should be stable.

2. **Probe Analysis**:
   - Probe 4.5: 100% failure on subject length - agent generates correct content but fails length constraint
   - Probe 6.2: 20% max-steps failures - agent gets stuck in reasoning loops, can't self-assess when to stop
   - Probe 7.1: 100% auth bypass on baseline - agent proceeds without checking, lacks self-monitoring

3. **Pattern**: The agent often produces good outputs but cannot reliably assess their own quality or adherence to constraints.

**Solution**: A trained judge/critic that can:
- Provide rejection sampling during generation
- Gate outputs before delivery  
- Enable rollback when quality drops
- Assess constraint adherence (length, tone, factual accuracy)

## Training Method: SimPO (Reference-Free)

**Choice Rationale** (citing Meng, Xia, and Chen, NeurIPS 2024):
- **Lower compute cost**: No reference model needed vs DPO
- **Better small-data performance**: SimPO shows stronger results on <2K preference pairs
- **Simpler training**: Single model vs DPO's dual-model setup

**Alternative considered**: ORPO (Hong, Lee, and Thorne, EMNLP 2024) - similar benefits but SimPO has stronger empirical results on instruction-following tasks similar to our use case.

## Dataset Construction Methodology

### Final Dataset Statistics (v0.1)

| Metric | Value |
|--------|-------|
| Total tasks | 250 |
| Valid tasks | 250 / 250 (100%) |
| Contamination check | PASSED — 0 violations |
| Train partition | 126 tasks (50%) |
| Dev partition | 74 tasks (30%) |
| Held-out partition | 50 tasks (20%) |
| Probes covered | 33 / 33 |

**Category distribution:**
- workflow_correctness: 112 (45%)
- resource_honesty: 52 (21%)
- signal_grounding: 44 (18%)
- tone_consistency: 42 (17%)

**Source mode distribution:**
- hand_authored: 83 (33%)
- programmatic: 72 (29%)
- multi_llm_synthesis: 56 (22%)
- trace_derived: 39 (16%)

**Contamination check results** (see `dataset/contamination_check.json`):
- N-gram overlap (10-gram threshold): 0 violations
- Embedding similarity (Jaccard fallback, threshold 0.85, min 8 tokens): 0 violations
- Time-shift verification: 0 violations

*Note: 10-gram threshold used instead of paper's 8-gram default. Justification: narrow B2B sales domain shares vocabulary by design (e.g., "We need N senior X engineers"). See synthesis memo 03 for full argument.*

### Four-Mode Generation Strategy

Actual final counts (v0.1) differ from initial targets because hand-authored tasks proved
higher-fidelity than synthesis at our seed scale (see synthesis memo 01 for the argument).
Initial targets are shown for transparency.

**1. Trace-Derived (actual: 39 tasks, initial target: 75)**
- Source: Week 10 `trace_log.jsonl` — 8 real agent traces
- Method: Extract real prospect interactions, redact PII, structure as evaluation tasks.
  Each trace expanded into 4–6 variants by varying prospect context while preserving the
  real failure pattern.
- Ceiling: 8 traces × ~5 variants = ~40 tasks. Target of 75 was over-optimistic given
  the trace corpus size (see synthesis memo 01).
- Example trace IDs: `llm_gap_analysis_7a52cdcf_3/_5/_7` (tone drift), `llm_gap_analysis_1d816fd2_2` (cost pathology)

**2. Programmatic (actual: 72 tasks, initial target: 75)**
- Source: Parameter sweep templates
- Method: Combinatorial expansion of:
  - Company size: [25, 50, 100, 500+] employees
  - AI maturity: [0, 1, 2, 3]
  - Signal confidence: [low, medium, high]
  - Bench match: [0%, 50%, 100%] capacity overlap
- Focus: Systematic coverage of input space. Programmatic tasks are honest about coverage
  because the parameter axes are independently meaningful.

**3. Multi-LLM Synthesis (actual: 56 tasks, initial target: 62)**
- Source: Hand-authored seeds expanded via LLM generation with judge filtering
- Method:
  - Claude Sonnet 4.6 for adversarial edge cases (synthesis batches 1–3)
  - Qwen3-Next-80B for bulk variations
  - Quality filter: separate judge model scores each generated task; tasks scoring <3/5
    on coherence + verifiability are rejected before inclusion
- Model routing: generation model family ≠ judge model family (Li et al., 2025)
- Focus: Hard cases that stress-test failure modes — adversarial personas, legal/cultural
  edge cases, multi-turn booking failures

**4. Hand-Authored (actual: 83 tasks, initial target: 38)**
- Source: Manual construction targeting probe gaps
- Method: Craft scenarios that exploit specific weaknesses from probe library
- Exceeded target because hand-authored tasks have the highest probe-to-task fidelity —
  each task traces directly to a documented failure mode with no synthesis noise
- Focus: Regulatory constraints (GDPR/CCPA), multi-prospect coordination, enrichment
  edge cases that synthesis missed

### Partitioning Rationale

The 50/30/20 split is chosen for the following reasons:

- **Train (50%, 126 tasks):** SimPO preference pair construction requires ~1,500 pairs from
  ~126 tasks (≈12 pairs/task via chosen/rejected generation). A larger train partition would
  leave too few tasks for reliable dev-set iteration.
- **Dev (30%, 74 tasks):** Judge calibration requires enough tasks to measure correlation
  between dev-tier and eval-tier judges (target: ≥50 tasks per category for statistical
  power). 74 tasks across 4 categories gives ~18 per category — sufficient for calibration
  but not for final ablations.
- **Held-out (20%, 50 tasks):** Delta A/B/C ablations require a sealed partition large enough
  for paired bootstrap significance testing (p<0.05 requires ≥30 pairs; 50 gives headroom).
  20% is the minimum that provides statistical validity while preserving training data volume.

Partitioning is stratified by (category × difficulty) with deterministic seed=42 to ensure
category distribution is consistent across all three partitions.

### Contamination Prevention Protocol

Following Chen et al. (EMNLP 2025) contamination prevention guidelines:

1. **N-gram Overlap Check**: 10-gram threshold (relaxed from paper's 8-gram default — see
   synthesis memo 03 for justification: narrow B2B domain shares vocabulary by design)
2. **Embedding Similarity**: Cosine similarity <0.85 using sentence-transformers (Jaccard
   fallback when sentence-transformers unavailable)
3. **Time-Shift Verification**: Public signal references must be documentably from specified
   time windows; funding dates older than 365 days are flagged
4. **Model Family Rotation**: Never use same model to generate and judge the same task

### Quality Assurance

**Inter-Rater Agreement**: 
- Hand-label 30 tasks against rubric
- Re-label same 30 tasks after 24h without seeing first labels  
- Require >80% agreement on each rubric dimension
- Revise rubric if agreement <80%, re-label

**Judge Calibration**:
- Spot-check 50 generated tasks with eval-tier model
- Compare dev-tier judge scores vs eval-tier scores
- Adjust judge prompts if correlation <0.8

## Training Data Preparation

**Preference Pair Construction**:
- **Chosen**: High-scoring outputs from trace log + corrected versions of failed outputs
- **Rejected**: Probe-triggered failures + synthetic bad examples (wrong tone, fabricated signals, over-commitments)
- **Target**: 1,500 preference pairs after quality filtering
- **Quality Gate**: Both chosen and rejected must pass basic schema validation

**Preference Leakage Prevention** (Li et al., 2025):
- Use different model families for chosen-rewrites vs judging
- Route: GPT-4.1 for corrections, Qwen3-Next for quality assessment
- Never let same model generate and evaluate the same example

## Evidence Chain Integrity

Every numeric claim in final publication will trace to:
- **Week 10 Trace IDs**: Real agent behavior examples
- **Probe IDs**: Documented failure mode instances  
- **Ablation Results**: Measured performance deltas
- **Cost Logs**: Resource consumption tracking

This ensures full reproducibility and prevents unsupported claims.