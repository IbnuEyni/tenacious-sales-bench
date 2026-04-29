# Methodology: Tenacious-Bench Construction and Training Path

## Path Selection: Path B - DPO Judge/Critic

**Justification from Week 10 Evidence:**

Based on analysis of trace IDs and probe results, the primary failure mode is **inconsistency** rather than generation quality:

1. **Trace Evidence**: 
   - `llm_gap_analysis_7a52cdcf_3` through `llm_gap_analysis_7a52cdcf_7` show correct individual responses but inconsistent quality across turns
   - `llm_ai_maturity_c0033ad8_3` vs `llm_ai_maturity_850154ee_1` show similar inputs producing different confidence scores (0.325 vs 0.357 cost, similar token counts but different outputs)

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

**1. Trace-Derived (30% - 75 tasks)**
- Source: Week 10 `trace_log.jsonl` entries
- Method: Extract real prospect interactions, redact PII, structure as evaluation tasks
- Focus: Multi-turn conversations showing actual failure patterns
- Example trace IDs: `llm_gap_analysis_7a52cdcf_*` series (tone degradation over turns)

**2. Programmatic (30% - 75 tasks)**  
- Source: Parameter sweep templates
- Method: Combinatorial expansion of:
  - Company size: [25, 50, 100, 500+] employees
  - AI maturity: [0, 1, 2, 3] 
  - Signal confidence: [low, medium, high]
  - Bench match: [0%, 50%, 100%] capacity overlap
- Focus: Systematic coverage of input space

**3. Multi-LLM Synthesis (25% - 62 tasks)**
- Source: LLM generation with judge filtering
- Method: 
  - Claude Sonnet 4.6 for adversarial edge cases
  - Qwen3-Next-80B for bulk variations
  - Quality filter using separate judge model
- Focus: Hard cases that stress-test failure modes

**4. Hand-Authored Adversarial (15% - 38 tasks)**
- Source: Manual construction targeting probe gaps
- Method: Craft scenarios that exploit specific weaknesses from probe library
- Focus: Regulatory constraints, multi-prospect coordination, edge cases synthesis missed

### Contamination Prevention Protocol

Following Chen et al. (EMNLP 2025) contamination prevention guidelines:

1. **N-gram Overlap Check**: <8-gram overlap between held-out and training tasks
2. **Embedding Similarity**: Cosine similarity <0.85 using sentence-transformers
3. **Time-Shift Verification**: Public signal references must be documentably from specified time windows
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