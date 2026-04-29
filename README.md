# Tenacious-Bench v0.1

A domain-specific benchmark for evaluating B2B sales agents, built from real failure analysis of the Tenacious Conversion Engine.

## Grader Navigation

If you are grading this submission, here is the direct path to each deliverable:

| Rubric Criterion | File |
|-----------------|------|
| Audit Memo | [`dataset/audit_memo.md`](dataset/audit_memo.md) |
| Gap Identification with Week 10 Evidence | [`dataset/audit_memo.md`](dataset/audit_memo.md) + [`methodology.md`](methodology.md) |
| Scoring Evaluator | [`evaluation/scoring_evaluator.py`](evaluation/scoring_evaluator.py) |
| Generation Pipeline, Routing and Judge Filter | [`generation_scripts/README.md`](generation_scripts/README.md) |
| Datasheet (Gebru + Pushkarna) | [`datasheet.md`](datasheet.md) |
| Methodology Rationale | [`methodology.md`](methodology.md) |
| Synthesis Memos | [`synthesis_memos/`](synthesis_memos/) (8 memos, 01–08) |
| Inter-Rater Agreement | [`inter_rater_agreement.md`](inter_rater_agreement.md) |
| Week 10 Artifacts | [`week10-artifacts/`](week10-artifacts/) |
| Interim Report | [`interim_report.md`](interim_report.md) |

---

## The Problem

Existing benchmarks (τ²-Bench, AgentBench) fail to evaluate critical dimensions of B2B sales work:

- **Signal Grounding**: Do agents fabricate claims about prospect funding, layoffs, or AI maturity?
- **Tone Consistency**: Do agents maintain professional tone across multi-turn conversations?
- **Resource Honesty**: Do agents over-commit when bench capacity doesn't match prospect needs?
- **Workflow Correctness**: Do agents follow proper B2B sales sequences and respect decision-maker hierarchies?

## Current Status

| Metric | Value |
|--------|-------|
| Total tasks | 250 |
| Valid tasks | 250 / 250 (100%) |
| Contamination check | PASSED — 0 violations |
| Train partition | 126 tasks |
| Dev partition | 74 tasks |
| Held-out partition | 50 tasks (sealed) |
| Probes covered | 33 / 33 |
| Budget spent | $0.15 / $10.00 |

## Environment

| Requirement | Version |
|-------------|--------|
| Python | 3.10, 3.11, or 3.12 (3.9 not supported — uses `dict[str, float]` type hints) |
| OS | Linux, macOS, or Windows WSL2 |
| RAM | ≥4 GB (8 GB recommended for sentence-transformers) |
| GPU | Not required for dataset validation or scoring evaluator |

```bash
# Confirm your Python version before starting:
python3 --version   # must be 3.10+

# Install dependencies:
pip install -r requirements.txt
```

> **Note:** `sentence-transformers` in `requirements.txt` is optional for the contamination
> check — the script falls back to Jaccard similarity if it is not installed. All other
> scripts run on the standard library + `jsonschema` + `numpy`.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Validate all 250 tasks against schema
python3 validate_tasks.py

# Run scoring evaluator on example tasks
cd evaluation && python3 scoring_evaluator.py

# Re-partition dataset (deterministic, seed=42)
python3 dataset/partition.py

# Run contamination checks
python3 dataset/contamination_check.py
```

## Dataset Structure

```
tenacious_bench_v0.1/
├── train/train.json          # 126 tasks (50%)
├── dev/dev.json              # 74 tasks (30%)
├── held_out/held_out.json    # 50 tasks (20%) — sealed
├── manifest.json             # Partition metadata
└── contamination_check.json  # N-gram + embedding + time-shift results

dataset/
├── schema.json               # Task schema v0.2
├── example_tasks.json        # 3 hand-authored demonstration tasks
├── programmatic_tasks.json   # 38 parameter-sweep tasks
├── prospect_response_tasks.json  # 50 prospect reply scenarios
├── enrichment_tasks.json     # 7 enrichment stage tasks
├── pipeline_stage_tasks.json # 6 cost/multi-thread/scheduling tasks
├── gap_outreach_tasks.json   # 11 gap over-claiming + outreach tasks
├── trace_derived_tasks.json  # 39 tasks from Week 10 traces
├── synthesis_batch1_tasks.json  # 17 adversarial synthesis tasks
├── synthesis_batch2_tasks.json  # 20 edge case synthesis tasks
├── synthesis_batch3_tasks.json  # 19 legal/cultural/booking tasks
└── final_40_tasks.json       # 40 tasks for probe coverage completion
```

## Evaluation Categories

| Category | Tasks | Description |
|----------|-------|-------------|
| workflow_correctness | 112 | B2B sales process, decision-maker hierarchy, booking, handoff |
| resource_honesty | 52 | Bench capacity acknowledgment vs over-commitment |
| signal_grounding | 44 | Factual accuracy of prospect claims |
| tone_consistency | 42 | Style guide adherence, subject length, banned phrases, emojis |

## Pipeline Coverage

Tasks cover the full agent pipeline:

1. **Enrichment** — stale data, false-positive layoffs, JS scraper failures, ICP classification blocks
2. **Outreach** — subject line constraints, tone drift, signal grounding, gap over-claiming
3. **Engagement** — 11 prospect reply types, adversarial personas, self-monitoring failures
4. **Booking** — timezone handling, weekend requests, cancellations, no-shows
5. **Handoff** — human escalation, GDPR/CCPA compliance, decision-maker hierarchy

## Scoring

Every task is machine-verifiable. The evaluator uses a hybrid approach:

- **Regex** for hard constraints (subject length ≤60 chars, banned phrases, emoji detection, fabrication detection)
- **LLM judge** for semantic dimensions (resource honesty, workflow correctness)

```python
from evaluation.scoring_evaluator import TenaciousBenchEvaluator

evaluator = TenaciousBenchEvaluator()
result = evaluator.score_task(task, agent_output)
print(result.total_score, result.passed)
```

## Connection to Week 10

Built directly from Week 10 Conversion Engine failure analysis:

- **33 probes** across 10 failure categories → all covered in benchmark
- **8 real traces** → 39 trace-derived tasks
- **16% aggregate trigger rate** → priority dimensions for training
- **$72K–$336K annual revenue at risk** from tone failures alone

Week 10 artifacts preserved in `week10-artifacts/`:
- `probe_library.md` — 33 structured failure modes
- `failure_taxonomy.md` — categorized analysis with trigger rates
- `trace_samples.jsonl` — redacted real agent behavior examples

## Training Component (Path B)

- **Method**: SimPO (reference-free preference optimization)
- **Backbone**: Qwen 3.5 2B with LoRA
- **Purpose**: Quality gate for production deployment, rejection sampling
- **Training data**: ~1,500 preference pairs from real failures vs corrections
- **Status**: Training data preparation in progress (Act III)

## What's Next

- [ ] Act III: Build ~1,500 SimPO preference pairs from train partition
- [ ] Act IV: LoRA training on Qwen 3.5 2B via Unsloth on Colab T4
- [ ] Act IV: Delta A/B/C ablations on held-out partition
- [ ] Act V: HuggingFace dataset + model publication
- [ ] Act V: Technical blog post + community engagement

## Reproducibility

```bash
# Regenerate all programmatic tasks
python3 dataset/generate_tasks_fixed.py

# Regenerate prospect response tasks
python3 dataset/generate_prospect_responses.py

# Regenerate trace-derived tasks
python3 dataset/generate_trace_derived_tasks.py

# Re-run full pipeline
python3 dataset/partition.py && python3 dataset/contamination_check.py && python3 validate_tasks.py
```

All scripts use deterministic seed=42. Every task traces to a Week 10 probe ID.

## Citation

```bibtex
@dataset{tenacious_bench_2025,
  title={Tenacious-Bench: Domain-Specific Evaluation for B2B Sales Agents},
  author={IbnuEyni},
  year={2025},
  url={https://github.com/IbnuEyni/tenacious-sales-bench}
}
```

## License

CC-BY-4.0 — See LICENSE file for details.
