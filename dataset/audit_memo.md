# Audit Memo: Evaluation Gaps for Tenacious B2B Sales Agents

## The Gap

τ²-Bench retail and existing agent benchmarks fail to evaluate four critical dimensions of Tenacious-style B2B sales work:

**1. Signal Grounding Accuracy**
Existing benchmarks don't validate factual claims about prospects. Probe 2.3 shows our agent correctly avoids fabricating funding data (0/4 failures), but no benchmark tests this. Probe 9.1 reveals we lack freshness checks on 6+ month old Crunchbase data - a credibility destroyer that τ²-Bench cannot detect.

**2. Tone Consistency Under Pressure** 
τ²-Bench measures task completion but ignores style drift across multi-turn conversations. Probe 4.5 shows 100% failure rate on subject line length (78 chars vs 60 limit). Trace IDs `llm_gap_analysis_7a52cdcf_3` through `llm_gap_analysis_7a52cdcf_7` show tone degradation over 4 turns - the agent starts professional but drifts toward generic marketing language.

**3. Resource Honesty vs Over-Commitment**
No benchmark tests capacity constraints. Probe 3.1 shows correct behavior (acknowledging Rust gap when bench has 0 Rust engineers), but Probe 3.3 remains untested - what happens when bench capacity changes mid-conversation? Trace `out_enrichment_complete_c0033ad8_4` shows segment classification as "n/a" when signals are ambiguous, but no benchmark rewards this honesty.

**4. Domain Workflow Understanding**
τ²-Bench retail tasks don't require B2B sales process knowledge. Our agent handles discovery call booking (traces `out_email_send_c0033ad8_7`, `out_email_send_850154ee_5`) but no benchmark evaluates whether it follows proper qualification sequences or respects decision-maker hierarchies.

## Evidence from Week 10

**Probe Library Analysis**: 33 probes across 10 categories, 19 tested, 4 active failures:
- Probe 4.5: Subject length (1/1 failures) 
- Probe 6.2: Reasoning loops (6/30 failures in τ²-Bench)
- Probe 7.1: Auth bypass (5/5 failures on baseline)
- Probe 8.1: Timezone handling (1/1 failures)

**Trace Evidence**: 200+ interactions show systematic gaps:
- Cost pathology: `llm_gap_analysis_1d816fd2_2` consumed 7,314 tokens (4x normal)
- Signal confidence inconsistency: AI maturity scores vary 0-3 for similar inputs
- Multi-turn degradation: Professional tone in turn 1, marketing speak by turn 4

**Business Impact**: 16% aggregate trigger rate across tested probes. At 60 outbound/week, this costs 3-10 lost replies weekly, or $72K-$336K annual revenue at risk.

## What Tenacious-Bench Must Measure

A Tenacious-specific benchmark must evaluate:
1. **Factual accuracy** of public signal claims with source verification
2. **Tone adherence** to style guide across multi-turn conversations  
3. **Capacity honesty** when bench resources don't match prospect needs
4. **Workflow correctness** for B2B sales sequences and decision-maker respect

These dimensions are invisible to τ²-Bench retail but critical for Tenacious's "grounded, not generic" positioning. The benchmark must be machine-verifiable while capturing the nuanced failures that destroy credibility with senior engineering leaders.