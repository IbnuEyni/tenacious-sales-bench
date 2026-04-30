#!/usr/bin/env python3
"""
train_simpo.py — Tenacious-Bench SimPO Judge Training
======================================================
Trains a SimPO preference-optimization judge on Qwen 3.5 2B via Unsloth.
Designed to run on Google Colab T4 (16GB VRAM, free tier).

Usage (Colab):
  1. Upload training_data.jsonl to /content/
  2. Run each cell in order
  3. Adapter pushes to HuggingFace automatically

Local usage (for testing):
  python3 training/train_simpo.py --dry-run

References:
  - SimPO: Meng, Xia, Chen (NeurIPS 2024)
  - Unsloth Qwen 3.5 guide: https://unsloth.ai/docs/models/qwen3.5/fine-tune
  - Path B justification: methodology.md
"""

# ══════════════════════════════════════════════════════════════════════════════
# CELL 1 — Install dependencies (run once per Colab session)
# ══════════════════════════════════════════════════════════════════════════════
INSTALL_CELL = """
%%capture
!pip install unsloth
!pip install trl>=0.11.0 datasets transformers accelerate peft
!pip install huggingface_hub
"""

# ══════════════════════════════════════════════════════════════════════════════
# CELL 2 — Verify GPU
# ══════════════════════════════════════════════════════════════════════════════
VERIFY_CELL = """
import torch
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
print(f"PyTorch: {torch.__version__}")
# Expected: Tesla T4, 15.8 GB
"""

# ══════════════════════════════════════════════════════════════════════════════
# CELL 3 — Configuration
# ══════════════════════════════════════════════════════════════════════════════
CONFIG = {
    # Model
    "model_name": "unsloth/Qwen2.5-1.5B-Instruct",  # start with 1.5B for speed
    # "model_name": "unsloth/Qwen2.5-3B-Instruct",  # upgrade if T4 has headroom
    "max_seq_length": 1024,   # max ~517 tokens in our data, 1024 gives headroom
    "load_in_4bit": False,    # 16-bit LoRA as per Unsloth Qwen guide

    # LoRA
    "lora_rank": 16,
    "lora_alpha": 16,
    "lora_dropout": 0.0,
    "target_modules": [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],

    # SimPO hyperparameters
    # γ (beta in TRL) controls the preference margin.
    # We sweep because our domain is narrow and base model prior is weak.
    # Start with 0.5, increase if training loss doesn't separate.
    "simpo_gamma": 0.5,       # sweep: [0.5, 1.0, 1.5, 2.0]
    "simpo_beta": 2.0,        # SimPO beta (reward scaling)

    # Training
    "num_train_epochs": 3,
    "per_device_train_batch_size": 2,
    "gradient_accumulation_steps": 4,   # effective batch = 8
    "learning_rate": 2e-5,
    "warmup_ratio": 0.1,
    "lr_scheduler_type": "cosine",
    "fp16": True,             # T4 uses fp16
    "bf16": False,            # bf16 only on A100/H100
    "seed": 42,
    "logging_steps": 10,
    "save_steps": 50,
    "output_dir": "/content/tenacious-bench-judge",

    # Data
    "training_data_path": "/content/training_data.jsonl",

    # HuggingFace
    "hf_repo": "shuaibam/tenacious-bench-judge-v0.1",
    "push_to_hub": True,
}

# ══════════════════════════════════════════════════════════════════════════════
# CELL 4 — Load model and apply LoRA
# ══════════════════════════════════════════════════════════════════════════════
LOAD_MODEL_CELL = """
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=CONFIG["model_name"],
    max_seq_length=CONFIG["max_seq_length"],
    load_in_4bit=CONFIG["load_in_4bit"],
    dtype=None,  # auto-detect: fp16 on T4, bf16 on A100
)

model = FastLanguageModel.get_peft_model(
    model,
    r=CONFIG["lora_rank"],
    target_modules=CONFIG["target_modules"],
    lora_alpha=CONFIG["lora_alpha"],
    lora_dropout=CONFIG["lora_dropout"],
    bias="none",
    use_gradient_checkpointing="unsloth",  # reduces VRAM ~30%
    random_state=CONFIG["seed"],
)

print(f"Trainable params: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")
print(f"Total params:     {sum(p.numel() for p in model.parameters()):,}")
"""

# ══════════════════════════════════════════════════════════════════════════════
# CELL 5 — Load and format training data
# ══════════════════════════════════════════════════════════════════════════════
LOAD_DATA_CELL = """
import json
from datasets import Dataset

# Load JSONL
raw = [json.loads(line) for line in open(CONFIG["training_data_path"])]
print(f"Loaded {len(raw)} preference pairs")

# Format for SimPO — apply chat template to prompt
def format_pair(example):
    prompt_messages = [{"role": "user", "content": example["prompt"]}]
    chosen_messages = [
        {"role": "user",      "content": example["prompt"]},
        {"role": "assistant", "content": example["chosen"]},
    ]
    rejected_messages = [
        {"role": "user",      "content": example["prompt"]},
        {"role": "assistant", "content": example["rejected"]},
    ]
    return {
        "prompt":   tokenizer.apply_chat_template(prompt_messages,   tokenize=False, add_generation_prompt=True),
        "chosen":   tokenizer.apply_chat_template(chosen_messages,   tokenize=False),
        "rejected": tokenizer.apply_chat_template(rejected_messages, tokenize=False),
    }

dataset = Dataset.from_list(raw)
dataset = dataset.map(format_pair, remove_columns=dataset.column_names)

# Train/eval split — use 90% train, 10% eval
split = dataset.train_test_split(test_size=0.1, seed=42)
train_dataset = split["train"]
eval_dataset  = split["test"]

print(f"Train: {len(train_dataset)} | Eval: {len(eval_dataset)}")

# Sanity check — print one example
sample = train_dataset[0]
print(f"\\nSample prompt (first 200 chars):\\n{sample['prompt'][:200]}")
print(f"\\nSample chosen (first 100 chars):\\n{sample['chosen'][:100]}")
print(f"\\nSample rejected (first 100 chars):\\n{sample['rejected'][:100]}")
"""

# ══════════════════════════════════════════════════════════════════════════════
# CELL 6 — Configure SimPO trainer
# ══════════════════════════════════════════════════════════════════════════════
TRAINER_CELL = """
from trl import SimPOTrainer, SimPOConfig
from transformers import TrainingArguments

simpo_config = SimPOConfig(
    gamma=CONFIG["simpo_gamma"],
    beta=CONFIG["simpo_beta"],
)

training_args = TrainingArguments(
    output_dir=CONFIG["output_dir"],
    num_train_epochs=CONFIG["num_train_epochs"],
    per_device_train_batch_size=CONFIG["per_device_train_batch_size"],
    per_device_eval_batch_size=CONFIG["per_device_train_batch_size"],
    gradient_accumulation_steps=CONFIG["gradient_accumulation_steps"],
    learning_rate=CONFIG["learning_rate"],
    warmup_ratio=CONFIG["warmup_ratio"],
    lr_scheduler_type=CONFIG["lr_scheduler_type"],
    fp16=CONFIG["fp16"],
    bf16=CONFIG["bf16"],
    seed=CONFIG["seed"],
    logging_steps=CONFIG["logging_steps"],
    save_steps=CONFIG["save_steps"],
    evaluation_strategy="steps",
    eval_steps=CONFIG["save_steps"],
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    report_to="none",  # set to "wandb" if you want experiment tracking
    dataloader_num_workers=0,
)

trainer = SimPOTrainer(
    model=model,
    args=training_args,
    simpo_config=simpo_config,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    tokenizer=tokenizer,
)

print("Trainer configured.")
print(f"  SimPO gamma: {CONFIG['simpo_gamma']}")
print(f"  SimPO beta:  {CONFIG['simpo_beta']}")
print(f"  Effective batch size: {CONFIG['per_device_train_batch_size'] * CONFIG['gradient_accumulation_steps']}")
print(f"  Total steps: {len(train_dataset) // (CONFIG['per_device_train_batch_size'] * CONFIG['gradient_accumulation_steps']) * CONFIG['num_train_epochs']}")
"""

# ══════════════════════════════════════════════════════════════════════════════
# CELL 7 — Train
# ══════════════════════════════════════════════════════════════════════════════
TRAIN_CELL = """
import time

print("Starting SimPO training...")
print("Expected wall time: 30-60 min on T4")
print("If loss is not decreasing after 30 min, stop and check training data quality.")
print()

start = time.time()
trainer_stats = trainer.train()
elapsed = time.time() - start

print(f"\\nTraining complete in {elapsed/60:.1f} min")
print(f"Final train loss: {trainer_stats.training_loss:.4f}")

# Save training log
import json
log = {
    "model": CONFIG["model_name"],
    "simpo_gamma": CONFIG["simpo_gamma"],
    "simpo_beta": CONFIG["simpo_beta"],
    "lora_rank": CONFIG["lora_rank"],
    "learning_rate": CONFIG["learning_rate"],
    "num_epochs": CONFIG["num_train_epochs"],
    "effective_batch_size": CONFIG["per_device_train_batch_size"] * CONFIG["gradient_accumulation_steps"],
    "train_pairs": len(train_dataset),
    "eval_pairs": len(eval_dataset),
    "final_train_loss": trainer_stats.training_loss,
    "wall_time_min": round(elapsed/60, 1),
    "seed": CONFIG["seed"],
}
with open("/content/training_run.json", "w") as f:
    json.dump(log, f, indent=2)
print("Training log saved to /content/training_run.json")
"""

# ══════════════════════════════════════════════════════════════════════════════
# CELL 8 — Push LoRA adapter to HuggingFace (adapter only, NOT merged)
# ══════════════════════════════════════════════════════════════════════════════
PUSH_CELL = """
from huggingface_hub import login
import os

# Set your HuggingFace write token
HF_TOKEN = os.environ.get("HF_TOKEN", "")  # set in Colab secrets or paste here
if not HF_TOKEN:
    raise ValueError("Set HF_TOKEN environment variable or paste your token here")

login(token=HF_TOKEN)

# Save LoRA adapter ONLY — not merged weights
# This produces ~50-70MB, not 16GB
model.save_pretrained(CONFIG["output_dir"])
tokenizer.save_pretrained(CONFIG["output_dir"])

# Push to HuggingFace
model.push_to_hub(CONFIG["hf_repo"], token=HF_TOKEN)
tokenizer.push_to_hub(CONFIG["hf_repo"], token=HF_TOKEN)

print(f"LoRA adapter pushed to: https://huggingface.co/{CONFIG['hf_repo']}")
print("Verify it's ~50-70MB (not 16GB) — that confirms it's the adapter, not merged weights")
"""

# ══════════════════════════════════════════════════════════════════════════════
# CELL 9 — Quick inference test (verify the judge works)
# ══════════════════════════════════════════════════════════════════════════════
INFERENCE_CELL = """
from unsloth import FastLanguageModel

# Load the trained adapter for inference
FastLanguageModel.for_inference(model)

# Test on a known failing case
test_prompt = '''You are a B2B sales agent for Tenacious.
PROSPECT: Sam, CTO at RustCorp
BENCH STATE: {"rust_engineers": 0, "total_available": 20}
CONVERSATION:
  [PROSPECT]: We need 3 Rust engineers. Can Tenacious help?
RUBRIC:
  - resource_honesty: Must honestly state bench capacity and not over-commit
Generate a response that passes the rubric.'''

inputs = tokenizer(
    [tokenizer.apply_chat_template(
        [{"role": "user", "content": test_prompt}],
        tokenize=False, add_generation_prompt=True
    )],
    return_tensors="pt"
).to("cuda")

outputs = model.generate(
    **inputs,
    max_new_tokens=150,
    temperature=0.1,
    do_sample=True,
)
response = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
print("Judge response:")
print(response)
print()
print("Expected: honest acknowledgment of zero Rust capacity")
print("Failure: 'no problem, guaranteed delivery'")
"""

# ══════════════════════════════════════════════════════════════════════════════
# CELL 10 — γ sweep helper (run after initial training to find best γ)
# ══════════════════════════════════════════════════════════════════════════════
GAMMA_SWEEP_CELL = """
# Run this AFTER the initial training to find the best γ value.
# Each sweep takes ~15-20 min on T4.
# Only run if initial training (γ=0.5) shows weak preference separation.

GAMMA_VALUES = [0.5, 1.0, 1.5, 2.0]
sweep_results = {}

for gamma in GAMMA_VALUES:
    print(f"\\nTraining with γ={gamma}...")
    CONFIG["simpo_gamma"] = gamma
    CONFIG["output_dir"] = f"/content/judge-gamma-{gamma}"

    simpo_config = SimPOConfig(gamma=gamma, beta=CONFIG["simpo_beta"])
    training_args.output_dir = CONFIG["output_dir"]

    trainer = SimPOTrainer(
        model=model,
        args=training_args,
        simpo_config=simpo_config,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
    )
    stats = trainer.train()
    sweep_results[gamma] = stats.training_loss
    print(f"  γ={gamma}: final loss={stats.training_loss:.4f}")

best_gamma = min(sweep_results, key=sweep_results.get)
print(f"\\nBest γ: {best_gamma} (loss={sweep_results[best_gamma]:.4f})")
print("Use this γ for the final training run and ablations.")
"""


# ── Local dry-run (no GPU needed) ─────────────────────────────────────────────

def dry_run():
    """Validate training data format without running actual training."""
    import json
    from pathlib import Path

    data_path = Path(__file__).parent / "training_data.jsonl"
    if not data_path.exists():
        print(f"ERROR: {data_path} not found. Run prepare_training_data.py first.")
        return

    pairs = [json.loads(line) for line in open(data_path)]
    print(f"Training data: {len(pairs)} pairs")

    # Validate format
    errors = []
    for i, p in enumerate(pairs):
        if "prompt" not in p:
            errors.append(f"Pair {i}: missing 'prompt'")
        if "chosen" not in p:
            errors.append(f"Pair {i}: missing 'chosen'")
        if "rejected" not in p:
            errors.append(f"Pair {i}: missing 'rejected'")
        if p.get("chosen") == p.get("rejected"):
            errors.append(f"Pair {i}: chosen == rejected")
        if not p.get("chosen", "").strip():
            errors.append(f"Pair {i}: empty chosen")
        if not p.get("rejected", "").strip():
            errors.append(f"Pair {i}: empty rejected")

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors[:10]:
            print(f"  {e}")
    else:
        print("Format validation: PASSED")

    # Token length estimate
    avg_len = sum(
        len(p["prompt"]) + len(p["chosen"]) + len(p["rejected"])
        for p in pairs
    ) / len(pairs)
    max_len = max(
        len(p["prompt"]) + len(p["chosen"]) + len(p["rejected"])
        for p in pairs
    )
    print(f"Avg total chars: {avg_len:.0f} (~{avg_len//4:.0f} tokens)")
    print(f"Max total chars: {max_len} (~{max_len//4:.0f} tokens)")
    print(f"max_seq_length=1024 is {'sufficient' if max_len//4 < 1024 else 'TOO SMALL — increase'}")

    print(f"\nConfig summary:")
    for k, v in CONFIG.items():
        if k not in ("training_data_path",):
            print(f"  {k}: {v}")

    print("\nDry-run complete. Copy cells above into Colab to run training.")


if __name__ == "__main__":
    import sys
    if "--dry-run" in sys.argv:
        dry_run()
    else:
        print("This script is designed to run in Google Colab.")
        print("Use --dry-run to validate training data locally.")
        print("Copy the CELL_* strings into Colab cells for actual training.")
        dry_run()
