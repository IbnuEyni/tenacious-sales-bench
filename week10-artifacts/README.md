# Week 10 Artifacts

Essential references from the Tenacious Conversion Engine (Week 10) that provide evidence for the Tenacious-Bench evaluation framework.

## Files

### `probe_library.md`
- **Purpose**: 33 structured probes documenting specific failure modes
- **Usage**: Task generation seeds, evidence for gap analysis
- **Key Probes**: 4.5 (subject length), 3.1-3.2 (resource honesty), 2.3 (signal fabrication)

### `failure_taxonomy.md`  
- **Purpose**: Categorized analysis of probe results with trigger rates
- **Usage**: Priority ranking for benchmark dimensions
- **Key Finding**: 16% aggregate trigger rate, highest in cost pathology (16%) and dual-control (100%)

### `trace_samples.jsonl`
- **Purpose**: Redacted examples of real agent interactions
- **Usage**: Evidence for multi-turn behavior, cost patterns, inconsistency issues
- **Key Traces**: 
  - `llm_gap_analysis_7a52cdcf_*`: Multi-turn tone consistency
  - `llm_gap_analysis_1d816fd2_2`: Cost pathology (7,314 tokens)
  - `out_enrichment_complete_c0033ad8_4`: Honest segment classification

## Evidence Chain

Every claim in the Tenacious-Bench methodology traces back to these artifacts:

| Claim | Evidence Source |
|-------|----------------|
| "Subject line length failures" | Probe 4.5 + email traces |
| "Multi-turn tone drift" | trace_samples.jsonl: 7a52cdcf sequence |
| "Cost pathology 16% rate" | failure_taxonomy.md Category 6 |
| "Resource honesty behavior" | Probes 3.1-3.2 + segment=n/a traces |

## Full Context

For complete Week 10 implementation details:
- **Source Repository**: [Link to Week 10 repo when published]
- **Complete Trace Log**: 200+ interactions (too large for this repo)
- **Agent Source Code**: Full implementation details

These artifacts provide sufficient context for Tenacious-Bench evaluation while maintaining clean separation between Week 10 and Week 11 deliverables.