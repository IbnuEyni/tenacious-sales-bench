# Week 11 Implementation Status

## ✅ Completed (Act I - Day 1)

### Core Infrastructure
- **Project Structure**: Separate `week11-tenacious-bench/` folder within existing repo
- **Audit Memo**: 600-word gap analysis identifying 4 key dimensions τ²-Bench misses
- **Schema Design**: Machine-verifiable JSON schema with 4 scoring dimensions
- **Scoring Evaluator**: Working implementation with regex + LLM judge methods
- **Cost Tracking**: Budget monitoring system ($10 total, $0.15 spent so far)

### Dataset Foundation
- **Example Tasks**: 3 hand-crafted tasks demonstrating schema
- **Programmatic Generator**: 12 tasks across 2 categories (tone_consistency, resource_honesty)
- **Task Distribution**: 
  - Categories: tone_consistency (6), resource_honesty (6)
  - Difficulties: easy (2), medium (8), hard (2)
  - Source modes: programmatic (12), hand_authored (3)

### Methodology
- **Path Selection**: Path B (DPO Judge/Critic) with SimPO training
- **Evidence Chain**: All claims trace to Week 10 probe IDs and trace IDs
- **Quality Assurance**: Inter-rater agreement protocol, contamination prevention

## 🔄 Next Steps (Acts II-V)

### Act II - Dataset Authoring (Days 2-3)
- [ ] Trace-derived tasks (75 tasks from Week 10 trace_log.jsonl)
- [ ] Multi-LLM synthesis (62 tasks using Claude + Qwen3-Next)
- [ ] Hand-authored adversarial (38 tasks targeting probe gaps)
- [ ] Quality filtering and contamination checks
- [ ] Dataset partitioning (train 50%, dev 30%, held-out 20%)

### Act III - Training Data Prep (Day 4)
- [ ] Preference pair construction (1,500 chosen/rejected pairs)
- [ ] SimPO data formatting
- [ ] Contamination prevention validation

### Act IV - Training & Ablation (Days 5-6)
- [ ] LoRA training on Qwen 3.5 2B (Unsloth/Colab T4)
- [ ] Delta A: Trained vs baseline on Tenacious-Bench held-out
- [ ] Delta B: Trained vs prompt-engineered judge
- [ ] Cost-Pareto analysis

### Act V - Publication (Day 7)
- [ ] HuggingFace dataset with datasheet
- [ ] HuggingFace model with model card
- [ ] Technical blog post (1,500 words)
- [ ] Community engagement (GitHub issue)

## 📊 Current Metrics

**Budget**: $9.85 remaining / $10.00 total
**Tasks Generated**: 15 total (12 programmatic + 3 examples)
**Target**: 250 tasks total
**Progress**: 6% complete on dataset construction

## 🔗 Evidence Chain Integrity

Every implementation decision traces back to Week 10:
- **Probe 4.5** → Subject length tasks (TB_PROG_001-006)
- **Probe 3.1, 3.2** → Resource honesty tasks (TB_PROG_007+)
- **Trace IDs** → Multi-turn conversation patterns
- **Failure taxonomy** → 16% trigger rate → priority dimensions

## 🎯 Success Criteria

- [x] Machine-verifiable scoring system
- [x] Schema validates against JSON Schema Draft 7
- [x] Cost tracking under budget
- [ ] >80% inter-rater agreement on hand-labeled subset
- [ ] >5pp improvement on held-out (Delta A)
- [ ] Statistical significance p<0.05
- [ ] Complete reproducibility documentation