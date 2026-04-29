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

---

## Multi-LLM Synthesis Pipeline

The pipeline is implemented in [`multi_llm_pipeline.py`](multi_llm_pipeline.py) — a runnable
script that encodes the routing table, judge thresholds, pairwise dedup logic, and seed
controls in code. Run it directly:

```bash
# Dry-run (no API calls, tests pipeline logic against existing batch files):
python3 generation_scripts/multi_llm_pipeline.py --dry-run --batch 1

# Full run (requires OPENROUTER_API_KEY):
OPENROUTER_API_KEY=<key> python3 generation_scripts/multi_llm_pipeline.py --batch 1
OPENROUTER_API_KEY=<key> python3 generation_scripts/multi_llm_pipeline.py --batch 2
OPENROUTER_API_KEY=<key> python3 generation_scripts/multi_llm_pipeline.py --batch 3

# Override seed (default: 42):
python3 generation_scripts/multi_llm_pipeline.py --dry-run --batch 1 --seed 123
```

### Model Routing Table

| Batch | Generation Model | Judge Model | Probe Focus |
|-------|-----------------|-------------|-------------|
| synthesis_batch1 | Claude Sonnet 4.6 | Qwen3-Next-80B | Adversarial personas (4.4, 7.1, 7.2) |
| synthesis_batch2 | Claude Sonnet 4.6 | Qwen3-Next-80B | Edge cases (3.3, 9.1, 9.3, 2.3) |
| synthesis_batch3 | GPT-4.1 | Qwen3-Next-80B | Legal/cultural/booking (7.1, 4.2, 8.1) |

Generation model family ≠ judge model family in every batch. This is a hard rule, not a
recommendation — see preference leakage prevention below.

### Full Pipeline Flow

```
Week 10 probe seeds (hand-authored)
    │
    ▼
Generation (Claude Sonnet 4.6 / GPT-4.1)
    │  Prompt: "Generate a B2B sales evaluation task for probe {probe_id}.
    │           Vary: {parameter_axes}. Output: JSON matching schema v0.2."
    │
    ▼
Schema validation (validate_tasks.py)
    │  Rejects: malformed JSON, missing required fields, invalid task_id pattern
    │  Rejection rate: ~12% of raw generated tasks
    │
    ▼
Quality filter (Qwen3-Next-80B judge)
    │  Scores each task on three axes (1–5 each):
    │    - Input coherence: Is the prospect scenario internally consistent?
    │    - Ground-truth verifiability: Can a human unambiguously determine pass/fail?
    │    - Rubric clarity: Are the scoring criteria specific enough to apply?
    │  Threshold: mean score ≥ 3.5/5.0 required for inclusion
    │  Rejection rate: ~18% of schema-valid tasks
    │
    ▼
Contamination check (contamination_check.py)
    │  Three-stage dedup — see Dedup Logic section below
    │  Rejection rate: 0 violations in final dataset
    │
    ▼
Stratified partition (partition.py, seed=42)
    │  50% train / 30% dev / 20% held-out
    │  Stratified by (category × difficulty)
    │
    ▼
Final dataset (250 tasks, 0 contamination violations)
```

### Preference Leakage Prevention (Li et al., 2025)

Preference leakage occurs when the same model family generates and judges the same data —
the judge systematically prefers outputs matching its own distributional biases, inflating
quality scores for its own generations by 12–18% (Li et al., Table 1).

Three mitigations applied:

**1. Model-family rotation (hard rule)**
Generation and judging never use the same model family:
- Claude family generates → Qwen family judges
- GPT family generates → Qwen family judges
- Qwen family never generates synthesis tasks (it is reserved for judging)

**2. Constraint-anchored judging for hard-constraint dimensions**
For dimensions with deterministic pass/fail criteria (subject length ≤ 60, banned phrases,
required fields), the judge is replaced by regex/schema checks. Preference leakage cannot
affect a string length comparison. This reduces the surface area where leakage can operate
from 4 dimensions to 2 (resource_honesty and workflow_correctness only).

**3. Rubric-anchored judge prompts**
The judge prompt passes the task's `criteria` field explicitly rather than asking for
open-ended quality assessment. This anchors the judge to the task's specific requirements
rather than its own quality priors:

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

**4. Metadata tracking**
Every task's `metadata` records `generation_model` and `judge_model`, enabling post-hoc
leakage analysis. If a future audit finds systematic score inflation for a specific
generation/judge pair, affected tasks can be re-judged.

---

## Dedup Logic

Three-stage contamination prevention (Chen et al., EMNLP 2025):

**Stage 1 — N-gram overlap (10-gram threshold)**
- Operates on discriminative content only: `signal_brief` + `bench_state` + `expected_behavior`
- Excludes shared domain vocabulary in `conversation_history` templates
- 10-gram threshold (relaxed from paper's 8-gram default) — see synthesis memo 03 for
  justification: narrow B2B domain shares vocabulary by design ("We need N senior X engineers")
- Flags any held-out task sharing a 10-gram with any train task

**Stage 2 — Embedding similarity (Jaccard fallback, threshold 0.85)**
- Uses sentence-transformers when available (preferred)
- Falls back to Jaccard word overlap when sentence-transformers not installed
- Skips tasks with <8 discriminative tokens (sparse signal briefs)
- Catches semantic duplicates that use different surface vocabulary

**Stage 3 — Time-shift verification**
- Flags funding dates older than 365 days
- Ensures signal references are documentably from specified time windows
- Prevents tasks from referencing "recent" events that are no longer recent

---

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
