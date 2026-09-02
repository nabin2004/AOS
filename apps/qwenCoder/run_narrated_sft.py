#!/usr/bin/env python3
"""Continued SFT Fine-Tuning on 400 Narrated Manim Trajectories.

Continues fine-tuning from an existing Hugging Face SFT LoRA adapter
(e.g., nabin2004/AOS-qwen3-8b-adapter or nabin2004/AOS-qwen2.5-coder-7b-manim-sft)
on the voiceover-annotated dataset, and pushes the updated LoRA adapter
to Hugging Face Hub.

Usage:
    uv run python run_narrated_sft.py
    uv run python run_narrated_sft.py --base-model Qwen/Qwen3-8B \
        --init-adapter nabin2004/AOS-qwen3-8b-adapter \
        --hub-adapter-repo nabin2004/AOS-qwen3-8b-narrated-adapter \
        --push-to-hub
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Optional

import torch
from datasets import load_dataset
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    PreTrainedTokenizerBase,
    TrainingArguments,
)
from trl import SFTTrainer

try:
    from huggingface_hub import HfApi, get_token
except ImportError:
    HfApi = None
    get_token = None

QWEN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = QWEN_ROOT.parent.parent

DEFAULT_BASE_MODEL = "Qwen/Qwen3-8B"
DEFAULT_INIT_ADAPTER = "nabin2004/AOS-qwen3-8b-adapter"
DEFAULT_HUB_ADAPTER_REPO = "nabin2004/AOS-qwen3-8b-narrated-adapter"
DEFAULT_DATA_PATH = QWEN_ROOT / "data_narrated_sft" / "train.jsonl"
DEFAULT_OUTPUT_DIR = QWEN_ROOT / "qwen3-8b-narrated-sft"


def _resolve_hf_token() -> str | None:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token and get_token:
        try:
            token = get_token()
        except Exception:
            token = None
    return token or None


def load_tokenizer(model_id: str) -> PreTrainedTokenizerBase:
    token = _resolve_hf_token()
    tokenizer = AutoTokenizer.from_pretrained(model_id, token=token, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    return tokenizer


def load_policy_model(
    base_model_id: str,
    init_adapter: str | None = None,
    use_4bit: bool = True,
    lora_r: int = 32,
    lora_alpha: int = 64,
) -> Any:
    """Load base model in QLoRA 4-bit and attach initial LoRA adapter (or create new)."""
    token = _resolve_hf_token()
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16

    bnb_config = None
    if use_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True,
        )

    print(f"Loading base model: {base_model_id} (compute_dtype: {compute_dtype})")
    model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=compute_dtype,
        token=token,
        trust_remote_code=True,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)

    if init_adapter:
        print(f"Attaching starting LoRA adapter: {init_adapter}")
        try:
            model = PeftModel.from_pretrained(
                model,
                init_adapter,
                is_trainable=True,
                token=token,
            )
            print("Successfully loaded and initialized trainable adapter.")
            return model
        except Exception as exc:
            print(f"Notice: Could not load initial adapter '{init_adapter}' ({exc}). Initializing fresh LoRA.")

    print(f"Initializing fresh LoRA adapter (r={lora_r}, alpha={lora_alpha})...")
    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model


def prepare_chat_dataset(data_path: Path, tokenizer: PreTrainedTokenizerBase):
    """Load JSONL dataset and format chat messages using the tokenizer chat template."""
    raw_ds = load_dataset("json", data_files=str(data_path), split="train")

    def format_chat(sample):
        messages = sample.get("messages", [])
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
        return {"text": text}

    formatted_ds = raw_ds.map(format_chat, remove_columns=raw_ds.column_names)
    return formatted_ds


def push_adapter_to_hub(
    adapter_dir: Path,
    repo_id: str,
    base_model_id: str,
    token: Optional[str] = None,
    private: bool = False,
) -> None:
    """Push the trained LoRA adapter to Hugging Face Hub."""
    if HfApi is None:
        raise ImportError("huggingface-hub is required for hub upload.")

    resolved_token = token or _resolve_hf_token()
    if not resolved_token:
        print("WARNING: No HF_TOKEN available; skipping Hub upload.", file=sys.stderr)
        return

    api = HfApi(token=resolved_token)
    print(f"Creating/updating LoRA adapter repository: https://huggingface.co/{repo_id}")
    api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True, private=private, token=resolved_token)

    print(f"Uploading adapter folder: {adapter_dir} -> {repo_id}")
    api.upload_folder(
        folder_path=str(adapter_dir),
        repo_id=repo_id,
        repo_type="model",
        token=resolved_token,
    )

    readme_content = f"""---
license: apache-2.0
base_model: {base_model_id}
tags:
- manim
- manim-voiceover
- text-to-speech
- aos
- lora
- sft
---

# {repo_id.split('/')[-1]}

Fine-tuned LoRA adapter on **400 Narrated Manim Trajectories** using `manim-voiceover`.

## Features
- **Pedagogical Audio Grounding**: Synthesizes synchronized `VoiceoverScene` Python scripts.
- **Timing Synchronization**: Generates animations bounded by `run_time=tracker.duration`.
- **Phonetic LaTeX**: Spoken voiceover scripts express formulas verbally without raw LaTeX syntax errors.

## Base Model
- `{base_model_id}`
"""
    readme_path = adapter_dir / "README.md"
    readme_path.write_text(readme_content, encoding="utf-8")
    api.upload_file(
        path_or_fileobj=str(readme_path),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="model",
        token=resolved_token,
    )
    print(f"Successfully pushed adapter to: https://huggingface.co/{repo_id}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Continued SFT fine-tuning on 400 narrated Manim trajectories")
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL, help=f"Base model ID (default: {DEFAULT_BASE_MODEL})")
    parser.add_argument("--init-adapter", default=DEFAULT_INIT_ADAPTER, help="Initial LoRA adapter from Hugging Face or path")
    parser.add_argument("--data-path", type=Path, default=DEFAULT_DATA_PATH, help=f"Dataset JSONL (default: {DEFAULT_DATA_PATH})")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help=f"Output adapter dir (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--hub-adapter-repo", default=DEFAULT_HUB_ADAPTER_REPO, help=f"Hugging Face repo ID (default: {DEFAULT_HUB_ADAPTER_REPO})")
    parser.add_argument("--epochs", type=int, default=2, help="Training epochs (default: 2)")
    parser.add_argument("--lr", type=float, default=5e-5, help="Learning rate (default: 5e-5)")
    parser.add_argument("--seq-len", type=int, default=2048, help="Sequence length (default: 2048)")
    parser.add_argument("--batch-size", type=int, default=1, help="Per-device batch size (default: 1)")
    parser.add_argument("--grad-accum", type=int, default=4, help="Gradient accumulation steps (default: 4)")
    parser.add_argument("--push-to-hub", action="store_true", help="Push trained adapter to Hugging Face Hub")
    parser.add_argument("--smoke", action="store_true", help="Smoke test (1 step, small dataset)")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    data_path = args.data_path.resolve()
    output_dir = args.output_dir.resolve()

    if not data_path.is_file():
        print(f"ERROR: Dataset not found at: {data_path}")
        print("Run: uv run python prepare_narrated_datasets.py")
        return 1

    print("=================================================================")
    print("🚀 Starting Continued SFT Fine-Tuning (Manim Voiceover)")
    print(f"Base Model:    {args.base_model}")
    print(f"Init Adapter:  {args.init_adapter}")
    print(f"Dataset:       {data_path}")
    print(f"Output Dir:    {output_dir}")
    print(f"Hub Repo:      {args.hub_adapter_repo}")
    print("=================================================================")

    tokenizer = load_tokenizer(args.base_model)
    model = load_policy_model(args.base_model, init_adapter=args.init_adapter)

    train_dataset = prepare_chat_dataset(data_path, tokenizer)
    if args.smoke:
        train_dataset = train_dataset.select(range(min(4, len(train_dataset))))
        args.epochs = 1

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=0.05,
        logging_steps=10,
        save_strategy="epoch",
        optim="paged_adamw_8bit",
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        report_to="none",
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=train_dataset,
        dataset_text_field="text",
        max_seq_length=args.seq_len,
        tokenizer=tokenizer,
        args=training_args,
    )

    print("\nStarting training loop...")
    trainer.train()

    print(f"\nSaving updated adapter to: {output_dir}")
    trainer.model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    if args.push_to_hub:
        push_adapter_to_hub(
            adapter_dir=output_dir,
            repo_id=args.hub_adapter_repo,
            base_model_id=args.base_model,
        )

    print("\n🎉 Continued SFT Fine-Tuning Completed Successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
