#!/usr/bin/env python3
"""Finetune Qwen3-8B on ManimCE SFT Dataset using Unsloth and SFTTrainer.

Supports:
- 4-bit / 16-bit QLoRA with Unsloth speedups.
- Qwen Chat Template formatting.
- Automatic dataset loading from local JSONL or Hugging Face Hub (nabin2004/AOS-Manim-SFT).
- Checkpoint saving and LoRA adapter export.

Usage:
    uv run python finetune_qwen3.py --dataset-repo nabin2004/AOS-Manim-SFT
    uv run python finetune_qwen3.py --data-path ./data/train.jsonl
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import torch
from datasets import load_dataset
from transformers import TrainingArguments
from trl import SFTTrainer

try:
    from unsloth import FastLanguageModel
    HAS_UNSLOTH = True
except ImportError:
    HAS_UNSLOTH = False
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import LoraConfig, get_peft_model


def train(args: argparse.Namespace) -> None:
    print(f"Loading base model: {args.model_name}...")

    if HAS_UNSLOTH:
        print("Using Unsloth FastLanguageModel for 2x-5x faster training & 50% VRAM savings.")
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=args.model_name,
            max_seq_length=args.max_seq_length,
            dtype=None,
            load_in_4bit=args.load_in_4bit,
        )

        model = FastLanguageModel.get_peft_model(
            model,
            r=args.lora_r,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            bias="none",
            use_gradient_checkpointing="unsloth",
            seed=args.seed,
        )
    else:
        print("Unsloth not found. Using standard transformers + PEFT.")
        tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            args.model_name,
            torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            device_map="auto",
            trust_remote_code=True,
        )
        peft_config = LoraConfig(
            r=args.lora_r,
            lora_alpha=args.lora_alpha,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            lora_dropout=args.lora_dropout,
            bias="none",
            task_type="CAUSAL_LM",
        )
        model = get_peft_model(model, peft_config)

    # Load dataset
    if args.data_path and Path(args.data_path).is_file():
        print(f"Loading local dataset: {args.data_path}")
        dataset = load_dataset("json", data_files=str(args.data_path), split="train")
    else:
        print(f"Loading Hub dataset: {args.dataset_repo}")
        dataset = load_dataset(args.dataset_repo, split="train")

    def formatting_prompts_func(examples):
        texts = tokenizer.apply_chat_template(
            examples["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )
        return {"text": texts}

    dataset = dataset.map(formatting_prompts_func, batched=True)

    training_args = TrainingArguments(
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        warmup_steps=args.warmup_steps,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        logging_steps=5,
        optim="adamw_8bit" if torch.cuda.is_available() else "adamw_torch",
        weight_decay=0.01,
        lr_scheduler_type="cosine",
        seed=args.seed,
        output_dir=args.output_dir,
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=args.max_seq_length,
        dataset_num_proc=1 if sys.platform == "win32" else 4,
        packing=False,
        args=training_args,
    )

    print("\nStarting SFT Training...")
    trainer.train()

    save_path = Path(args.output_dir) / "final_adapter"
    print(f"\nSaving LoRA adapter to: {save_path}")
    model.save_pretrained(str(save_path))
    tokenizer.save_pretrained(str(save_path))
    print("Training complete.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Finetune Qwen3-8B on ManimCE SFT Dataset")
    parser.add_argument("--model-name", default="Qwen/Qwen3-8B", help="Base model Hugging Face ID")
    parser.add_argument("--dataset-repo", default="nabin2004/AOS-Manim-SFT", help="HF dataset repo")
    parser.add_argument("--data-path", default=None, help="Optional local path to train.jsonl")
    parser.add_argument("--output-dir", default="./qwen3_manim_lora", help="Output directory")
    parser.add_argument("--max-seq-length", type=int, default=2048, help="Max sequence length")
    parser.add_argument("--load-in-4bit", action="store_true", default=True, help="Use 4-bit quantization")
    parser.add_argument("--lora-r", type=int, default=32, help="LoRA rank")
    parser.add_argument("--lora-alpha", type=int, default=16, help="LoRA alpha")
    parser.add_argument("--lora-dropout", type=float, default=0.05, help="LoRA dropout")
    parser.add_argument("--batch-size", type=int, default=2, help="Batch size per device")
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4, help="Gradient accumulation")
    parser.add_argument("--learning-rate", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--epochs", type=int, default=3, help="Training epochs")
    parser.add_argument("--warmup-steps", type=int, default=10, help="Warmup steps")
    parser.add_argument("--seed", type=int, default=3407, help="Random seed")
    args = parser.parse_args()

    train(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
