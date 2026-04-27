# Week 11 Repository Migration Plan

## Problem
Week 11 deliverables require separate GitHub repo submission, but we built within Week 10 repo structure.

## Solution: Create Separate `tenacious-sales-bench` Repository

### Step 1: Create New Repository Structure
```
tenacious-sales-bench/
├── dataset/                 # Tenacious-Bench construction
├── training/               # Model training artifacts  
├── evaluation/             # Scoring and ablations
├── publication/            # Public documentation
├── week10-artifacts/       # MINIMAL Week 10 references
│   ├── probe_library.md    # Copy of probe definitions
│   ├── failure_taxonomy.md # Copy of failure analysis
│   └── trace_samples.jsonl # Redacted trace examples
└── README.md              # Standalone project description
```

### Step 2: What to Copy vs Reference

**Copy to New Repo:**
- All `week11-tenacious-bench/` contents
- Essential Week 10 artifacts needed for evidence chain:
  - `probes/probe_library.md` → `week10-artifacts/probe_library.md`
  - `probes/failure_taxonomy.md` → `week10-artifacts/failure_taxonomy.md`
  - Selected traces from `eval/trace_log.jsonl` → `week10-artifacts/trace_samples.jsonl`

**Reference via Links:**
- Full Week 10 implementation (link to original repo)
- Complete trace logs (too large to copy)
- Week 10 agent source code (not needed for Week 11 evaluation)

### Step 3: Update Documentation

**New README.md:**
```markdown
# Tenacious Sales Evaluation Bench

Domain-specific benchmark for B2B sales agent evaluation, built from real failure analysis.

## Connection to Week 10
This benchmark is derived from the Tenacious Conversion Engine (Week 10):
- **Source Repository**: [link to Week 10 repo]
- **Probe Library**: 33 documented failure modes → benchmark task seeds
- **Trace Analysis**: 200+ real interactions → evidence for gap analysis
- **Failure Taxonomy**: 16% trigger rate → priority dimensions

## Quick Start
[Standalone instructions for Week 11 only]
```

### Step 4: Evidence Chain Preservation

**In methodology.md:**
```markdown
## Evidence Sources
- Probe 4.5 (subject length): See week10-artifacts/probe_library.md#probe-45
- Trace llm_gap_analysis_7a52cdcf_3: See week10-artifacts/trace_samples.jsonl
- Full Week 10 context: [link to original repo]
```

### Step 5: HuggingFace Dataset References
```yaml
# In dataset card
source_code: "https://github.com/[username]/tenacious-sales-bench"
related_work: "https://github.com/[username]/10Acweek10"  # Week 10 reference
```

## Benefits of This Approach

✅ **Clean Evaluation**: Week 11 repo is self-contained for grading
✅ **Evidence Preservation**: Key Week 10 artifacts copied over
✅ **Publication Ready**: HuggingFace can reference focused repo
✅ **Traceability**: Links maintain connection to full Week 10 context
✅ **Submission Clarity**: Meets deliverable requirements exactly

## Migration Steps

1. Create new GitHub repo: `tenacious-sales-bench`
2. Copy `week11-tenacious-bench/` contents to new repo root
3. Copy essential Week 10 artifacts to `week10-artifacts/`
4. Update all documentation with new structure
5. Test that evidence chain still works
6. Submit new repo URL for Week 11 deliverables

## File Size Considerations

**Keep in new repo** (~2MB total):
- Probe library and taxonomy (text files)
- 20-30 sample traces (redacted)
- Generated tasks and schema
- Documentation

**Reference via link** (~50MB+):
- Full trace logs
- Week 10 agent source code
- Large data files (Crunchbase, etc.)