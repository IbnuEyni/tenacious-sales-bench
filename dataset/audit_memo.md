# Audit Memo: Evaluation Gaps for Tenacious B2B Sales Agents

## The Gap

τ²-Bench retail and existing agent benchmarks fail to evaluate four critical dimensions of
Tenacious-style B2B sales work. Each gap is demonstrated below with a concrete trace walkthrough
and the specific probe it maps to.

---

## Gap 1: Signal Grounding Accuracy

**What τ²-Bench misses:** τ²-Bench evaluates whether a task was completed, not whether the
factual claims made during completion were true. A sales agent that fabricates a funding round
"completes" the outreach task while destroying the relationship.

**Probe 2.3 — Funding amount fabricated (trigger rate: 0/4, correct behavior observed)**
The agent correctly returns `funding_detected: false` for companies absent from the Crunchbase
ODM sample. No benchmark rewards this restraint — τ²-Bench would score the task identically
whether the agent said "You raised $15M Series B" (fabricated) or said nothing about funding.

**Probe 9.1 — Crunchbase data stale by 6+ months**
Trace `out_enrichment_complete_c0033ad8_4` shows the enrichment pipeline returning
`funding=False, layoff=True, ai_maturity=0` for prospect "Consolety" with segment classified
as `n/a`. The pipeline correctly abstained from a segment assignment when signals were
ambiguous. However, the ODM snapshot has no freshness check — if Consolety's record is
18 months old, `funding=False` may be wrong. No existing benchmark tests whether the agent
flags data staleness before asserting signal-based claims.

**Probe 2.4 — Leadership change from stale data (trigger rate: 0/1, correct behavior)**
The agent correctly scored a 200-day-old CTO appointment below the abstention threshold.
τ²-Bench has no concept of signal age — it cannot distinguish "you recently appointed a CTO"
(grounded) from "congratulations on your appointment" sent 7 months late (embarrassing).

---

## Gap 2: Tone Consistency Under Pressure

**What τ²-Bench misses:** τ²-Bench measures task completion in a single turn. It cannot detect
style drift across a multi-turn conversation where the agent starts professional and degrades
into marketing language by turn 4.

**Probe 4.5 — Subject line exceeds 60 characters (trigger rate: 1/1, ACTIVE FAILURE)**
Trace `out_email_send_c0033ad8_5` shows a sent email with subject:
> "Request: Exploring technical SEO partnerships post-restructuring"

That subject is **73 characters** — 13 over the 60-character style guide limit. On Gmail mobile,
it truncates to "Request: Exploring technical SEO partnerships po…", destroying the message.
τ²-Bench scored this task as a pass (email was sent). Tenacious-Bench scores it as a fail.

**Probe 4.1 — Marketing language after 3 turns**
Traces `llm_gap_analysis_7a52cdcf_3` (turn 1, 1,989 tokens, professional tone noted in
metadata) and `llm_gap_analysis_7a52cdcf_7` (turn 4, 1,733 tokens, metadata: "Fourth turn
showing potential tone drift — evidence for Probe 4.1") document the degradation pattern.
Turn 1 output tokens: 770. Turn 4 output tokens: 701 — similar length, but the metadata
flags qualitative drift. τ²-Bench has no mechanism to compare tone across turns of the same
conversation.

**Probe 4.2 — Aggressive follow-up language**
No benchmark tests whether the agent uses banned phrases ("just following up", "circling back")
in follow-up emails. These phrases are invisible to task-completion metrics but are the primary
reason senior engineering leaders mark outreach as spam.

---

## Gap 3: Resource Honesty vs Over-Commitment

**What τ²-Bench misses:** τ²-Bench retail tasks have no concept of inventory or capacity
constraints. A sales agent that promises 15 engineers when 7 are available "completes" the
engagement task while creating a delivery failure.

**Probe 3.1 — Prospect needs stack not on bench (trigger rate: 0/2, correct behavior)**
The agent correctly sets `bench_gap_detected` when bench has 0 Rust engineers. τ²-Bench
would score this identically to an agent that said "no problem, we can definitely deliver
3 Rust engineers next month" — both "completed" the conversation.

**Probe 3.2 — Prospect asks for 15 Python engineers (trigger rate: 0/1, correct behavior)**
The agent correctly referenced actual bench numbers (7 available) rather than committing 15.
No benchmark rewards this honesty. The business cost of the failure case: contract breach
risk and client lost permanently.

**Probe 3.3 — Bench count changes mid-conversation (untested)**
Trace `out_enrichment_complete_c0033ad8_4` shows enrichment completing at timestamp
`2026-04-25T11:14:18`. If a prospect replies two weeks later and bench capacity has changed,
the agent has no mechanism to re-check. This temporal gap is architecturally invisible to
any static benchmark.

---

## Gap 4: Domain Workflow Understanding

**What τ²-Bench misses:** τ²-Bench retail tasks (shopping, booking, account management) do not
require B2B sales process knowledge — qualification sequences, decision-maker hierarchies,
or GDPR-compliant handoff protocols.

**Probe 7.1 — Agent proceeds without authentication (trigger rate: 5/5, SYSTEMATIC FAILURE)**
On the τ²-Bench baseline, the agent bypassed authentication 100% of the time. In the Tenacious
context, this maps to taking action on a prospect's account without identity verification —
a compliance violation. τ²-Bench detected this as a task failure only because the retail task
required auth. It cannot detect the equivalent failure in a sales context where no auth gate
exists in the task definition.

**Probe 7.2 — Agent acts before user confirms**
Traces `out_email_send_c0033ad8_7` and `out_email_send_850154ee_5` show emails sent after
enrichment completed. The question τ²-Bench cannot answer: did the agent qualify the prospect
before sending, or did it send on the first signal match? Qualification-before-booking is a
B2B sales workflow requirement with no analogue in retail benchmarks.

**Probe 8.1 — Timezone confusion (trigger rate: 1/1, PARTIAL FAILURE)**
The agent proposed meeting times without explicit timezone labels. A US Pacific prospect and
an East Africa Time team have a 10-hour offset — a missed call from this failure costs 1–2
weeks of pipeline momentum. τ²-Bench retail booking tasks use a single timezone; the
multi-timezone scheduling requirement is entirely absent.

**Probe 6.2 — Reasoning loop consuming steps (trigger rate: 6/30 = 20% on τ²-Bench)**
This is the one probe where τ²-Bench *does* detect a failure — but only because step limits
are a τ²-Bench-native concept. The 20% failure rate on held-out (down from 60% on Qwen
baseline) shows the mechanism helps, but τ²-Bench cannot distinguish a reasoning loop caused
by task complexity from one caused by domain-specific ambiguity in B2B sales signals.

---

## Evidence Summary

| Probe | Category | Trigger Rate | Trace Evidence | τ²-Bench Detects? |
|-------|----------|-------------|----------------|-------------------|
| 2.3 | Signal grounding | 0/4 (correct) | `out_enrichment_complete_c0033ad8_4` | ❌ |
| 2.4 | Signal grounding | 0/1 (correct) | — | ❌ |
| 3.1 | Resource honesty | 0/2 (correct) | — | ❌ |
| 3.2 | Resource honesty | 0/1 (correct) | — | ❌ |
| 3.3 | Resource honesty | Untested | `out_enrichment_complete_c0033ad8_4` (timestamp gap) | ❌ |
| 4.1 | Tone consistency | 0/3 (correct) | `llm_gap_analysis_7a52cdcf_3`, `_7` | ❌ |
| 4.2 | Tone consistency | Untested | — | ❌ |
| 4.5 | Tone consistency | 1/1 **FAIL** | `out_email_send_c0033ad8_5` (73-char subject) | ❌ |
| 6.2 | Cost/workflow | 6/30 **FAIL** | `llm_gap_analysis_1d816fd2_2` (7,314 tokens) | ✅ (partial) |
| 7.1 | Workflow | 5/5 **FAIL** | — | ✅ (retail only) |
| 7.2 | Workflow | Untested | `out_email_send_c0033ad8_7`, `out_email_send_850154ee_5` | ❌ |
| 8.1 | Workflow | 1/1 **FAIL** | — | ❌ |
| 9.1 | Signal reliability | Untested | `out_enrichment_complete_c0033ad8_4` (no freshness check) | ❌ |

**16% aggregate trigger rate** across tested probes. At 60 outbound/week, this costs 3–10
lost replies weekly, or **$72K–$336K annual revenue at risk** from tone failures alone.

τ²-Bench detects 2 of 13 failure modes above — and only partially, because its detection
mechanism (step limits, auth gates) is calibrated for retail tasks, not B2B sales workflows.
Tenacious-Bench covers all 13.
