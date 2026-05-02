# Model Card — tenacious-bench-judge-v0.1

## Model Summary

A SimPO-trained preference judge for evaluating B2B sales agent outputs on
Tenacious-specific quality dimensions. Built as part of the TRP1 Week 11
challenge on top of `Qwen2.5-1.5B-Instruct` with LoRA (rank=16).

\*\*Huggin---
base_model: unsloth/Qwen2.5-1.5B-Instruct
tags:

- text-generation-inference
- transformers
- unsloth
- qwen2
- trl
  license: apache-2.0
  language:
- en

---

# Uploaded model

- **Developed by:** shuaibam
- **License:** apache-2.0
- **Finetuned from model :** unsloth/Qwen2.5-1.5B-Instruct

This qwen2 model was trained 2x faster with [Unsloth](https://github.com/unslothai/unsloth)

[<img src="https://raw.githubusercontent.com/unslothai/unsloth/main/images/unsloth%20made%20with%20love.png" width="200"/>](https://github.com/unslothai/unsloth)
gFace:** `shuaibam/tenacious-bench-judge-v0.1`
**Base model:** `unsloth/Qwen2.5-1.5B-Instruct`
**Adapter size:\*\* ~74MB (LoRA only, not merged)

---

## Intended Use

This model is a **quality gate judge** for B2B sales agents operating in the
Tenacious engineering staffing workflow. It scores agent outputs on four
dimensions:

| Dimension            | Description                                | Scoring method |
| -------------------- | ------------------------------------------ | -------------- |
| signal_accuracy      | Does the agent fabricate prospect data?    | Regex + judge  |
| tone_adherence       | Does the agent maintain professional tone? | Regex + judge  |
| resource_honesty     | Does the agent over-commit bench capacity? | Judge          |
| workflow_correctness | Does the agent follow B2B sales process?   | Judge          |

**Deployment pattern:** Rejection sampling — run the judge on agent output
before delivery. If score < 0.7, retry or escalate to human.

---

## Training

| Parameter            | Value                                  |
| -------------------- | -------------------------------------- |
| Training method      | SimPO via CPOTrainer (loss_type=simpo) |
| Framework            | Unsloth + TRL 0.24.0                   |
| Hardware             | Google Colab T4 (15.8GB VRAM)          |
| LoRA rank            | 16                                     |
| LoRA alpha           | 16                                     |
| Trainable parameters | 18,464,768 (1.18% of total)            |
| γ (SimPO margin)     | 1.5                                    |
| Learning rate        | 2e-5                                   |
| Epochs               | 3                                      |
| Effective batch size | 8                                      |
| Training pairs       | 599 (train + dev partitions)           |
| Wall time            | ~30 min                                |

**Training data:** 599 SimPO preference pairs generated from 200 tasks
(126 train + 74 dev) from Tenacious-Bench v0.1. Every pair traces to a
specific Week 10 probe ID and rubric criterion.

**Training results:**

```
Final reward accuracy:  100%
Final reward margin:    1.461
Final train loss:       1.556
Final eval loss:        0.960
```

---

## Evaluation — Ablation Results

Evaluated on 50 sealed held-out tasks from Tenacious-Bench v0.1.

| Metric    | Baseline (heuristic) | Trained judge | Prompted base |
| --------- | -------------------- | ------------- | ------------- |
| Avg score | 0.525                | 0.568         | 0.647         |
| Pass rate | 34.0%                | 30.0%         | 58.0%         |

**Delta A** (trained vs baseline): +0.043, 95% CI [-0.012, +0.103], p=0.065

- Positive effect — trained judge scores higher than heuristic baseline
- Not statistically significant at p<0.05 (just above threshold)
- Effect size doubled vs 370-pair run (+0.019 → +0.043)

**Delta B** (trained vs prompted): -0.079

- Prompted base model outperforms trained judge on pass rate
- Honest finding: prompt engineering is a strong baseline at this data scale
- Minimum viable dataset for significance estimated at ~700-800 pairs

---

## Limitations

1. **Below SimPO's tested minimum:** SimPO Appendix B tests down to ~1,000
   pairs. We trained on 599. Statistical significance was not achieved.

2. **Narrow domain:** This judge is calibrated for Tenacious B2B sales
   workflows only. Scores are not meaningful outside this domain.

3. **Heuristic fallback:** For regex-verifiable dimensions (subject length,
   banned phrases), the judge is not needed — deterministic checks are more
   reliable. The judge adds value only for semantic dimensions
   (resource_honesty, workflow_correctness).

4. **Base model prior:** Qwen2.5-1.5B-Instruct has no prior knowledge of
   Tenacious tone markers or bench capacity constraints. 599 pairs partially
   overcomes this but a larger dataset would produce stronger calibration.

---

## Intended Future Work (v0.2)

- Expand training data to ~1,000 pairs using additional trace-derived tasks
- Test Qwen3-1.7B-Instruct as backbone for stronger instruction following
- Add step-level process reward scoring for multi-turn trajectory evaluation
- Publish leaderboard on Tenacious-Bench held-out partition

---

## Citation

```bibtex
@misc{tenacious_bench_judge_2025,
  title={Tenacious-Bench Judge: SimPO-Trained Preference Judge for B2B Sales Agents},
  author={IbnuEyni},
  year={2025},
  url={https://huggingface.co/shuaibam/tenacious-bench-judge-v2-599pairs}
}
```

## License

CC-BY-4.0
