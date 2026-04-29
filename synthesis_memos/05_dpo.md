# Synthesis Memo: Direct Preference Optimization

**Paper:** Rafailov et al., NeurIPS 2023
**Category:** Path B — preference-tuned judge
**Date:** 2026-04-28

## Core Contribution

DPO eliminates the reward model and PPO training loop from RLHF by reparameterizing the reward function directly through the policy. The key insight (Equation 4): the optimal policy under a KL-constrained reward maximization objective can be expressed as a closed-form function of the reference policy and the reward. This allows training with a simple binary cross-entropy loss on (chosen, rejected) pairs, using the reference model's log-probabilities as the baseline.

## Key Design Choices Relevant to Tenacious-Bench

1. **Reference model requirement** (Section 3): DPO requires a frozen copy of the base model to compute log-probability ratios. This doubles memory during training.
2. **Preference pair quality** (Section 5.2): DPO is sensitive to noise in preference labels — mislabeled pairs degrade performance more than in PPO-based RLHF.
3. **β parameter** (Section 3, Equation 5): Controls deviation from the reference policy. Higher β = more conservative updates.

## Where I Disagree: The Reference Model Is a Liability at 2B Scale on Consumer GPUs

DPO's defining feature — the reference model — is also its primary practical limitation for our use case. Training a 2B-parameter judge on a Colab T4 (16GB VRAM):

- **DPO**: Requires the training model + frozen reference model in memory simultaneously. Qwen 3.5 2B in fp16 ≈ 4GB. Two copies = 8GB. Add LoRA adapters, optimizer states, and activations → ~14-15GB. This fits on T4 but leaves almost no headroom for batch size, forcing batch_size=1 or gradient accumulation that slows training 3-4x.

- **SimPO/ORPO**: Single model in memory. Same 4GB base + LoRA + optimizer ≈ 8-9GB. Batch size 4-8 is feasible, training completes 2-3x faster.

**Evidence from Week 10:**
- Our failure pattern is *inconsistency*, not *catastrophic generation failure*. Traces `llm_gap_analysis_7a52cdcf_3` through `_7` show the base model produces acceptable outputs most of the time. The judge needs to learn the *boundary* between acceptable and unacceptable — it doesn't need to be heavily regularized against the reference policy because the base model's prior is already reasonable for most inputs.
- Probe 4.5 (subject length) and Probe 7.1 (auth bypass) are binary pass/fail constraints. The preference signal is strong and unambiguous — chosen outputs satisfy the constraint, rejected outputs don't. DPO's β-controlled conservatism adds no value when the preference signal is this clear.

**My position:** DPO's reference model is a theoretical elegance that becomes a practical burden at our scale. SimPO's reference-free formulation achieves the same objective (align the model to preferences) without the memory overhead, and its implicit reward (average log-probability of the response) is a sufficient baseline for our domain where the preference signal is strong.

## What I Adopt from DPO

- The core insight that preference optimization can replace reward modeling — this is foundational regardless of which variant we use.
- The emphasis on preference pair quality (Section 5.2) — we apply strict quality filtering to our (chosen, rejected) pairs before training.
- The analytical framework for understanding what preference optimization is doing — even when using SimPO, understanding DPO's derivation helps diagnose training failures.
