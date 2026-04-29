# Generation Scripts

Reproducible authoring code for Tenacious-Bench v0.1.

## Scripts

| Script | Tasks Generated | Mode | Probes Targeted |
|--------|----------------|------|-----------------|
| `generate_tasks_fixed.py` | 38 | programmatic | 4.5, 3.1, 3.2, 2.1, 2.3, 7.2, 8.1, 8.3 |
| `generate_prospect_responses.py` | 50 | hand_authored | 4.2, 7.1, 7.2, 3.1, 3.2, 4.1, 4.3, 1.1, 5.1, 5.2, 3.3 |
| `generate_enrichment_tasks.py` | 7 | hand_authored | 9.3, 9.2, 2.4, 1.2, 1.3, 1.5, 1.4 |
| `generate_pipeline_tasks.py` | 6 | hand_authored | 5.2, 5.1, 6.1, 6.3, 8.2, 6.2 |
| `generate_gap_outreach_tasks.py` | 11 | hand_authored | 10.1, 10.2, 10.3, 2.1, 7.2, 4.2, 8.1, 3.1, 3.2, 7.1 |
| `generate_trace_derived_tasks.py` | 39 | trace_derived | 4.1, 4.3, 2.1, 2.2, 9.1, 9.2, 1.1, 1.4, 6.1, 4.5 |
| `generate_synthesis_batch1.py` | 17 | multi_llm_synthesis | 4.4, 7.1, 7.2, 4.2, 4.1, 4.3, 5.1, 3.3 |
| `generate_synthesis_batch2.py` | 20 | multi_llm_synthesis | 3.3, 7.2, 5.2, 3.1, 3.2, 2.1, 9.3, 9.1, 2.4, 2.3 |
| `generate_synthesis_batch3.py` | 19 | multi_llm_synthesis | 7.1, 4.2, 8.1, 3.2, 8.2 |
| `generate_final_40.py` | 40 | programmatic/hand_authored | 1.2, 1.3, 1.5, 10.2, 6.3, 8.2, 8.3, 4.4, 4.5, 2.1, 2.3, 3.1 |
| `partition.py` | — | utility | Stratified split, seed=42 |
| `contamination_check.py` | — | utility | N-gram, embedding, time-shift checks |

## Model Routes

### Multi-LLM Synthesis Pipeline

```
Seed prompts (hand-authored) 
    → Generation: hand_authored_seed (no external LLM calls for current batch)
    → Quality filter: validate_tasks.py (schema + quality checks)
    → Dedup: contamination_check.py (10-gram + Jaccard similarity)
    → Partition: partition.py (stratified, seed=42)
```

**Preference leakage prevention** (Li et al., 2025):
- Generation model family ≠ judge model family
- Current batch: hand-authored seeds (no LLM generation)
- Future batches: Claude/GPT for generation, Qwen3-Next for judging

### Judge Prompts

The scoring evaluator uses rubric-anchored prompting (Gu et al., 2024):

```python
prompt = (
    f"You are a strict B2B sales quality judge.\n"
    f"Dimension: {dimension}\n"
    f"Criteria: {config['criteria']}\n"
    f"Task input: {json.dumps(task['input'], indent=2)}\n"
    f"Agent output: {json.dumps(agent_output, indent=2)}\n\n"
    f"Score 0.0 (fail) or 1.0 (pass). Respond with JSON: "
    f'{{"score": <float>, "reasoning": "<one sentence>"}}'
)
```

## Dedup Logic

Three-stage contamination prevention:

1. **N-gram overlap** (10-gram threshold for narrow domain):
   - Extracts discriminative text only (prospect replies + signal brief)
   - Excludes agent openers and shared rubric phrases
   - Flags any held-out task sharing a 10-gram with any train task

2. **Embedding similarity** (Jaccard fallback, threshold 0.85, min 8 tokens):
   - Uses sentence-transformers when available
   - Falls back to Jaccard word overlap
   - Skips tasks with <8 discriminative tokens (sparse signal briefs)

3. **Time-shift verification**:
   - Flags funding dates older than 365 days
   - Ensures signal references are documentably from specified time windows

## Reproducibility

All scripts are deterministic given the same inputs. To reproduce the full dataset:

```bash
cd dataset
python3 generate_tasks_fixed.py
python3 generate_prospect_responses.py
python3 generate_enrichment_tasks.py
python3 generate_pipeline_tasks.py
python3 generate_gap_outreach_tasks.py
python3 generate_trace_derived_tasks.py
python3 generate_synthesis_batch1.py
python3 generate_synthesis_batch2.py
python3 generate_synthesis_batch3.py
python3 generate_final_40.py
cd ..
python3 validate_tasks.py
python3 dataset/partition.py
python3 dataset/contamination_check.py
```

Expected output: 250 valid tasks, 0 contamination violations.
