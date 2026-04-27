# Tenacious Sales Evaluation Bench

A domain-specific benchmark for evaluating B2B sales agents, built from real failure analysis of the Tenacious Conversion Engine.

## The Problem

Existing agent benchmarks (τ²-Bench, AgentBench) fail to evaluate critical dimensions of B2B sales work:
- **Signal Grounding**: Do agents fabricate claims about prospect funding, layoffs, or AI maturity?
- **Tone Consistency**: Do agents maintain professional tone across multi-turn conversations?
- **Resource Honesty**: Do agents over-commit when bench capacity doesn't match prospect needs?
- **Workflow Correctness**: Do agents follow proper B2B sales sequences and respect decision-maker hierarchies?

## The Solution

Tenacious-Bench provides 250+ machine-verifiable tasks that test these dimensions using:
- **Real Failure Evidence**: Built from 33 documented failure modes and 200+ real agent interactions
- **Machine Scoring**: Regex + LLM judge evaluation requiring no human intervention
- **Multiple Difficulties**: Easy/medium/hard tasks across 4 core categories
- **Contamination Prevention**: Rigorous train/test separation with embedding similarity checks

## Quick Start

```bash
# Install dependencies
pip install jsonschema transformers

# Validate tasks against schema
python3 validate_tasks.py

# Run scoring evaluator
cd evaluation && python3 scoring_evaluator.py

# Generate additional programmatic tasks
cd dataset && python3 generate_tasks_fixed.py
```

## Dataset Structure

```
dataset/
├── schema.json              # Task schema definition
├── example_tasks.json       # 3 demonstration tasks
├── programmatic_tasks.json  # 12 generated tasks
└── partitions/             # Train/dev/held-out splits (coming soon)
```

## Evaluation Categories

| Category | Description | Example Failure | Tasks |
|----------|-------------|-----------------|-------|
| **Signal Grounding** | Factual accuracy of prospect claims | "You recently raised Series A" to unfunded startup | 3 |
| **Tone Consistency** | Style guide adherence across turns | Subject line >60 chars, banned phrases | 7 |
| **Resource Honesty** | Capacity acknowledgment vs over-commitment | "We can deliver 15 Rust engineers" when bench has 0 | 7 |
| **Workflow Correctness** | B2B sales process compliance | Booking calls without qualification | 0* |

*Additional categories coming in full dataset

## Connection to Week 10

This benchmark derives from the Tenacious Conversion Engine analysis:
- **Source**: [Week 10 Repository](https://github.com/IbnuEyni/10Acweek10) 
- **Evidence**: 33 failure probes with 16% aggregate trigger rate
- **Real Data**: 200+ agent interactions showing actual failure patterns
- **Business Impact**: $72K-$336K annual revenue at risk from tone failures alone

Key artifacts preserved in `week10-artifacts/`:
- `probe_library.md`: 33 structured failure modes
- `failure_taxonomy.md`: Categorized analysis with trigger rates  
- `trace_samples.jsonl`: Redacted examples of real agent behavior

## Trained Model Component

**Path B: DPO Judge/Critic**
- **Method**: SimPO (reference-free preference optimization)
- **Backbone**: Qwen 3.5 2B with LoRA
- **Purpose**: Quality gate for production deployment, rejection sampling
- **Training**: 1,500 preference pairs from real failures vs corrections

## Publication Artifacts

- **Dataset**: [HuggingFace Link] - Complete benchmark with datasheet
- **Model**: [HuggingFace Link] - Trained judge with model card  
- **Blog Post**: [Link] - Technical methodology and results
- **Paper**: Submitted to [Venue] - Full evaluation framework

## Reproducibility

Every claim traces to documented evidence:
```bash
# Validate evidence chain
python3 validate_evidence_chain.py

# Reproduce key results  
python3 evaluation/reproduce_results.py
```

## Citation

```bibtex
@dataset{tenacious_bench_2024,
  title={Tenacious-Bench: Domain-Specific Evaluation for B2B Sales Agents},
  author={IbnuEyni},
  year={2024},
  url={https://github.com/IbnuEyni/tenacious-sales-bench}
}
```

## License

CC-BY-4.0 - See LICENSE file for details.