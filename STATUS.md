# Week 11 Implementation Status

## Completed (Act I — Enterprise Grade)

### Infrastructure
- **Schema v0.2**: Strict JSON Schema Draft 7 with `additionalProperties: false`, regex-validated task IDs, required `pass_threshold`, metadata support
- **Scoring Evaluator**: Pluggable LLM judge interface with heuristic fallback, proper error boundaries, dataclass results with `to_dict()` serialization
- **Task Validator**: Path-traversal-safe file loading, task ID uniqueness enforcement, category-specific field requirements, proper exit codes
- **Cost Tracker**: Timezone-aware UTC timestamps, thread-safe with locking, per-bucket budget limits, validation on inputs
- **Contamination Checks**: N-gram overlap (8-gram), embedding similarity (sentence-transformers with Jaccard fallback), time-shift verification
- **Partitioning**: Stratified split by (category, difficulty) with deterministic seed, manifest with distribution metadata
- **Package Structure**: `__init__.py` files, `requirements.txt`, pathlib throughout, logging instead of print

### Dataset (41 tasks, 16.4% of target)
- 3 hand-authored examples across 3 categories
- 38 programmatic tasks across all 4 categories (tone: 9, resource: 15, signal: 9, workflow: 5)
- 3 difficulty levels: easy (10), medium (19), hard (12)
- Partitioned: train (24), dev (13), held-out (4)
- Contamination check operational (catching real n-gram overlaps in programmatic templates)

### Documentation
- audit_memo.md (600 words, 8+ probe IDs, 5+ trace IDs)
- methodology.md (Path B declared, SimPO justified, 3 trace IDs, 2 papers cited)
- Cost log: $0.15 spent / $10.00 budget

## Next Steps

### Act II — Dataset Authoring (Days 2-3)
- [ ] Scale 41 → 250+ tasks using all 4 authoring modes
- [ ] Trace-derived tasks (~75) from Week 10 trace_samples.jsonl
- [ ] Multi-LLM synthesis (~62) via OpenRouter with judge filtering
- [ ] Hand-authored adversarial (~38) targeting untested probes
- [ ] Diversify programmatic templates to eliminate n-gram overlaps
- [ ] Re-partition and pass all contamination checks
- [ ] Inter-rater agreement (30-task hand-label + 24h re-label)
- [ ] Datasheet (Gebru 7-section + Pushkarna layered detail)

### Act III — Training Data Prep (Day 4)
- [ ] 1,500 preference pairs (chosen/rejected) for SimPO
- [ ] Preference leakage prevention (different model families)
- [ ] Contamination check against held-out

### Act IV — Train & Ablate (Days 5-6)
- [ ] LoRA on Qwen 3.5 2B via Unsloth on Colab T4
- [ ] Delta A: trained vs baseline on held-out (p<0.05)
- [ ] Delta B: trained vs prompt-engineered judge
- [ ] Cost-Pareto analysis

### Act V — Publish (Day 7)
- [ ] HuggingFace dataset + model
- [ ] Blog post (1,200-2,000 words)
- [ ] Community engagement
- [ ] CEO/CFO memo (2 pages)
- [ ] Demo video (6 min)

## Budget
- Spent: $0.15
- Remaining: $9.85
- Bucket: dataset_authoring ($0.15 / $5.00)
