# Methodology Rationale — Act III Training Data Preparation

## Path B: SimPO Judge — Why This Training Data Design

### Evidence from Week 10 Traces

Three traces directly motivate the preference pair construction strategy:

**Trace `llm_gap_analysis_7a52cdcf_7`** (tone drift, turn 4):
The agent produced professional output in turns 1-2 but drifted to marketing language by turn 4. The base model cannot self-assess this drift — it assigns similar log-probability to "We leverage our best-in-class talent" and "We place senior engineers vetted for technical depth." The preference pairs for tone_consistency tasks teach the judge to assign *lower* average log-probability to the marketing-language output, enabling rejection sampling before delivery.

**Trace `llm_ai_maturity_c0033ad8_3` vs `llm_ai_maturity_850154ee_1`**:
Similar inputs (AI maturity scoring) produced different confidence levels — one output asserted AI capability confidently, the other hedged. Neither was clearly wrong, but the inconsistency means the agent cannot reliably calibrate its own certainty. The signal_grounding preference pairs teach the judge to prefer hedged phrasing when signal confidence is low, and assertive phrasing when confidence is high — enforcing the calibration the base model lacks.

**Trace `out_email_send_c0033ad8_5`** (subject line 73 chars):
The agent generated a 73-character subject line despite the 60-character constraint. The base model's log-probability for the 73-char subject was not meaningfully lower than for a 55-char subject — it has no prior for this constraint. The tone_consistency preference pairs (negation variants) inject the constraint violation into the rejected output, teaching the judge to penalize length violations specifically.

### Why SimPO Over DPO (citing Meng et al., NeurIPS 2024)

SimPO's reference-free formulation (Section 3) eliminates the frozen reference model that DPO requires. On Colab T4 (16GB VRAM), DPO forces batch_size=1 due to dual-model memory requirements. SimPO runs at batch_size=2 with gradient_accumulation=4 (effective batch=8), producing more stable gradients on our 370-pair dataset.

SimPO's implicit reward — average log-probability of the response — is interpretable for production deployment: outputs the judge scores highly will have higher average log-probability, enabling threshold-based rejection sampling without a separate reward model call.

**Acknowledged limitation:** SimPO's Appendix B tests down to ~1,000 pairs. Our 370 pairs are below this minimum. We compensate by: (1) sweeping γ ∈ {0.5, 1.0, 1.5, 2.0} to find the margin that best separates our narrow domain, (2) using a narrow domain where fewer pairs may suffice, and (3) reporting the limitation honestly in Delta B.

### Why These Preference Pairs Are High Quality

Following Li et al. (2025) preference leakage prevention:
- Chosen outputs were written by human author (not LLM) — no model-family bias
- Rejected outputs are grounded in real probe-triggered failure patterns from Week 10, not synthetic bad examples
- No model was used to both generate and judge the same pair

Following LIMA (Zhou et al., NeurIPS 2023) quality-over-quantity principle:
- Every rejected output traces to a specific probe ID and documented failure mode
- Negation variants inject exactly one violation — not multiple — to produce clean preference signal
- Hard tasks get 2-3 variants targeting different failure modes, not paraphrases of the same failure

### Training Configuration Rationale

| Hyperparameter | Value | Reason |
|---|---|---|
| γ (SimPO margin) | 0.5 (sweep to 2.0) | Base model prior is weak on our domain — larger γ may be needed |
| LoRA rank | 16 | Standard for 1.5-2B models; higher rank risks overfitting at 370 pairs |
| Learning rate | 2e-5 | Conservative — prevents catastrophic forgetting of instruction-following |
| Epochs | 3 | Enough passes for 370 pairs; more risks overfitting |
| Effective batch | 8 | Stable gradients on small dataset |
| max_seq_length | 1024 | Max observed ~517 tokens; 1024 gives 2x headroom |
