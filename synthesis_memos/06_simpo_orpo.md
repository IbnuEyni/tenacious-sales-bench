# Synthesis Memo: SimPO and ORPO — Reference-Free Preference Optimization

**Papers:** Meng, Xia, and Chen, NeurIPS 2024 (SimPO); Hong, Lee, and Thorne, EMNLP 2024 (ORPO)
**Category:** Path B — preference-tuned judge
**Date:** 2026-04-28

## Core Contributions

**SimPO** replaces DPO's explicit reference model with an implicit reward: the average log-probability of the generated sequence. The loss encourages the model to assign higher average log-probability to chosen responses than rejected ones, with a margin γ. No reference model is loaded during training.

**ORPO** takes a different approach: it folds the preference signal into the supervised fine-tuning loss itself. A single training phase handles both instruction-following (SFT component) and preference alignment (odds-ratio penalty on rejected responses). This eliminates the separate SFT → DPO pipeline.

Both are reference-free, both reduce memory and compute, both claim competitive or superior results to DPO on standard benchmarks.

## Head-to-Head Comparison for Our Use Case

| Dimension | SimPO | ORPO |
|---|---|---|
| Memory (Qwen 3.5 2B, fp16, T4) | ~8-9GB (single model) | ~8-9GB (single model) |
| Training stages | 1 (preference only) | 1 (SFT + preference combined) |
| Assumes SFT base? | Yes — expects a model already instruction-tuned | No — handles SFT internally |
| Reported gains over DPO | +1.2pp AlpacaEval, +0.8pp MT-Bench (Table 3) | +0.5pp AlpacaEval (Table 2) |
| Small-data regime (<2K pairs) | Tested down to 500 pairs (Appendix B) | Primarily tested at 10K+ scale |

## My Choice: SimPO — and Where I Disagree with Both Papers

**I choose SimPO** for three reasons grounded in our evidence:

**1. Our base model is already instruction-tuned.** Qwen 3.5 2B is a post-trained model with instruction-following capability. ORPO's combined SFT+preference training is designed for base models that haven't been instruction-tuned yet. Running ORPO on an already-tuned model risks *undoing* useful instruction-following behavior during the SFT component. SimPO assumes an instruction-tuned base and only adjusts preferences — a better fit.

**2. SimPO has stronger small-data evidence.** Our training budget is ~1,500 preference pairs. SimPO's Appendix B shows stable training at 500 pairs. ORPO's experiments start at 10K+ pairs — extrapolating to our scale is risky.

**3. The average log-probability reward is interpretable for our domain.** SimPO's implicit reward (average log-prob) gives us a built-in confidence signal: outputs the judge scores highly will have higher average log-probability. This is directly useful for rejection sampling in production — we can threshold on log-probability without running a separate reward model.

**Where I disagree with SimPO:** Meng et al. claim (Section 4.3) that the average log-probability reward is "well-calibrated" across domains. I expect this to break for Tenacious-specific evaluation. Our Qwen 3.5 2B backbone has never seen B2B sales quality rubrics. Its prior log-probabilities for "good outreach email" vs "bad outreach email" are likely near-uniform — it doesn't know what Tenacious tone markers are.

**Evidence:** Traces `llm_ai_maturity_c0033ad8_3` (cost $0.000325) and `llm_ai_maturity_850154ee_1` (cost $0.000357) show similar token counts but different outputs for similar inputs. The base model treats both as equally plausible. SimPO's margin γ will need to be larger than the paper's default (γ=0.5) to overcome this weak prior — I plan to sweep γ ∈ {0.5, 1.0, 1.5, 2.0} during training.

**Where I disagree with ORPO:** Hong et al. present the combined SFT+preference loss as strictly beneficial (Section 3.2). For our case, it's a liability. We don't want to SFT the judge on sales email generation — we want it to *evaluate* sales emails. The SFT component would push the model toward generating sales-like text, which is orthogonal to our goal of scoring it.

## What I Adopt

- SimPO's reference-free loss function as the training objective.
- The margin parameter γ as a hyperparameter to sweep, not a fixed default.
- SimPO's average log-probability as a production-time rejection-sampling signal.
- From ORPO: the insight that preference and instruction-following can be trained jointly — useful if we later extend the judge to also generate corrected outputs (Path A+B hybrid in v0.2).
