#!/usr/bin/env python3
"""Clean DPO Pipeline for Aligning Manim Coder with Voiceover Trajectories.

Applies Direct Preference Optimization (DPO) to reinforce voiceover-narrated
`VoiceoverScene` code generation (chosen) over silent, un-narrated `Scene` code
(rejected) for identical mathematical and pedagogical visualization prompts.

Usage:
    uv run python run_narrated_dpo.py
    uv run python run_narrated_dpo.py --base-model Qwen/Qwen3-8B \\
        --sft-adapter nabin2004/AOS-qwen3-8b-narrated-adapter \\
        --hub-dpo-repo nabin2004/AOS-qwen3-8b-narrated-dpo \\
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
)
from trl import DPOConfig, DPOTrainer

try:
    from huggingface_hub import HfApi, get_token
except ImportError:
    HfApi = None
    get_token = None

QWEN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = QWEN_ROOT.parent.parent

DEFAULT_BASE_MODEL = "Qwen/Qwen3-8B"
DEFAULT_SFT_ADAPTER = "nabin2004/AOS-qwen3-8b-narrated-adapter"
DEFAULT_HUB_DPO_REPO = "nabin2004/AOS-qwen3-8b-narrated-dpo"
DEFAULT_DATA_PATH = QWEN_ROOT / "data_narrated_dpo" / "train.jsonl"
DEFAULT_OUTPUT_DIR = QWEN_ROOT / "qwen3-8b-narrated-dpo"


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


def load_dpo_model(
    base_model_id: str,
    sft_adapter: str | None = None,
    use_4bit: bool = True,
    use_8bit: bool = False,
    lora_r: int = 32,
    lora_alpha: int = 64,
) -> tuple[Any, LoraConfig | None]:
    """Load base model in QLoRA 4-bit or 8-bit and attach SFT adapter or create fresh LoRA."""
    token = _resolve_hf_token()
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16

    # Auto-detect Pascal P100 (sm_60) or GPUs without Tensor Cores for 4-bit
    if torch.cuda.is_available():
        major, minor = torch.cuda.get_device_capability(0)
        if major < 7 and use_4bit and not use_8bit:
            device_name = torch.cuda.get_device_name(0)
            print(
                f"✔ Pascal GPU detected ({device_name}, sm_{major}{minor}). "
                f"Auto-switching from 4-bit to 8-bit for native sm_60 DP4A compatibility."
            )
            use_4bit = False
            use_8bit = True

    bnb_config = None
    if use_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
            bnb_4bit_use_double_quant=True,
        )
    elif use_8bit:
        bnb_config = BitsAndBytesConfig(
            load_in_8bit=True,
        )

    print(
        f"Loading DPO policy model: {base_model_id} (compute_dtype: {compute_dtype}, "
        f"4bit={use_4bit}, 8bit={use_8bit})"
    )
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

    lora_config = LoraConfig(
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )

    if sft_adapter:
        print(f"Initializing DPO policy from SFT adapter: {sft_adapter}")
        try:
            model = PeftModel.from_pretrained(
                model,
                sft_adapter,
                is_trainable=True,
                token=token,
            )
            print("Successfully loaded SFT adapter into policy model.")
            return model, None
        except Exception as exc:
            print(f"Notice: Could not load initial adapter '{sft_adapter}' ({exc}). Initializing fresh PEFT LoRA.")

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model, lora_config


def push_dpo_adapter_to_hub(
    adapter_dir: Path,
    repo_id: str,
    base_model_id: str,
    sft_adapter: str | None = None,
    token: Optional[str] = None,
    private: bool = False,
) -> None:
    """Push DPO adapter to Hugging Face Hub."""
    if HfApi is None:
        raise ImportError("huggingface-hub is required for hub upload.")

    resolved_token = token or _resolve_hf_token()
    if not resolved_token:
        print("WARNING: No HF_TOKEN available; skipping Hub upload.", file=sys.stderr)
        return

    api = HfApi(token=resolved_token)
    print(f"Creating/updating DPO repository: https://huggingface.co/{repo_id}")
    api.create_repo(repo_id=repo_id, repo_type="model", exist_ok=True, private=private, token=resolved_token)

    print(f"Uploading DPO adapter folder: {adapter_dir} -> {repo_id}")
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
- dpo
- preference
- rlhf
- manim
- manim-voiceover
- aos
---

# {repo_id.split('/')[-1]}

Direct Preference Optimization (DPO) aligned LoRA adapter for **Manim Community Edition** mathematical and educational animation synthesis.

## Alignment Objective
Aligns the model to strongly prefer generating synchronized **`manim-voiceover`** code examples:
- **Chosen**: Clean `VoiceoverScene` scripts with `self.set_speech_service(GTTSService())`, animation duration tracking (`run_time=tracker.duration`), and phonetic mathematical explanations.
- **Rejected**: Silent, un-narrated standard `Scene` code.

## Lineage
- **Base LLM**: `{base_model_id}`
- **SFT Prior**: `{sft_adapter or 'Initialized LoRA'}`
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
    print(f"Successfully pushed DPO adapter to: https://huggingface.co/{repo_id}")


def _cast_trainable_fp32(model) -> None:
    """Ensure trainable parameters are float32 for PyTorch AMP GradScaler on Pascal/Turing GPUs."""
    n = 0
    for param in model.parameters():
        if param.requires_grad and param.dtype != torch.float32:
            param.data = param.data.to(torch.float32)
            n += 1
    if n:
        print(f"Cast {n} trainable adapter tensors to float32 for GradScaler")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Direct Preference Optimization (DPO) for Manim Voiceover generation")
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL, help=f"Base model ID (default: {DEFAULT_BASE_MODEL})")
    parser.add_argument("--sft-adapter", default=DEFAULT_SFT_ADAPTER, help=f"SFT adapter ID or path (default: {DEFAULT_SFT_ADAPTER})")
    parser.add_argument("--data-path", type=Path, default=DEFAULT_DATA_PATH, help=f"Preference JSONL path (default: {DEFAULT_DATA_PATH})")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--hub-dpo-repo", default=DEFAULT_HUB_DPO_REPO, help=f"HF DPO repo (default: {DEFAULT_HUB_DPO_REPO})")
    parser.add_argument("--beta", type=float, default=0.1, help="DPO temperature beta (default: 0.1)")
    parser.add_argument("--epochs", type=int, default=1, help="Training epochs (default: 1)")
    parser.add_argument("--lr", type=float, default=5e-6, help="Learning rate (default: 5e-6)")
    parser.add_argument("--batch-size", type=int, default=1, help="Per-device batch size (default: 1)")
    parser.add_argument("--grad-accum", type=int, default=4, help="Gradient accumulation steps (default: 4)")
    parser.add_argument("--max-length", type=int, default=2048, help="Max total sequence length (default: 2048)")
    parser.add_argument("--max-prompt-length", type=int, default=512, help="Max prompt length (default: 512)")
    parser.add_argument("--use-8bit", action="store_true", help="Use 8-bit quantization (recommended for Pascal P100 sm_60)")
    parser.add_argument("--no-4bit", action="store_true", help="Disable 4-bit quantization")
    parser.add_argument("--push-to-hub", action="store_true", help="Push DPO adapter to Hugging Face")
    parser.add_argument("--smoke", action="store_true", help="Smoke test (1 step, small dataset)")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    data_path = args.data_path.resolve()
    output_dir = args.output_dir.resolve()

    if not data_path.is_file():
        print(f"ERROR: DPO preference file not found at: {data_path}")
        print("Run: uv run python prepare_narrated_datasets.py")
        return 1

    print("=================================================================")
    print("🎯 Starting Direct Preference Optimization (DPO) Pipeline")
    print(f"Base Model:    {args.base_model}")
    print(f"SFT Adapter:   {args.sft_adapter}")
    print(f"DPO Dataset:   {data_path}")
    print(f"Beta (KL):     {args.beta}")
    print(f"Learning Rate: {args.lr}")
    print(f"Output Dir:    {output_dir}")
    print(f"Hub Repo:      {args.hub_dpo_repo}")
    print("=================================================================")

    tokenizer = load_tokenizer(args.base_model)
    use_4bit = not args.no_4bit and not args.use_8bit
    model, peft_config = load_dpo_model(
        args.base_model,
        sft_adapter=args.sft_adapter,
        use_4bit=use_4bit,
        use_8bit=args.use_8bit,
    )

    train_dataset = load_dataset("json", data_files=str(data_path), split="train")
    if args.smoke:
        train_dataset = train_dataset.select(range(min(4, len(train_dataset))))
        args.epochs = 1

    dpo_config = DPOConfig(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_steps=10,
        logging_steps=5,
        save_strategy="epoch",
        beta=args.beta,
        max_length=args.max_length,
        max_prompt_length=args.max_prompt_length,
        optim="paged_adamw_8bit",
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        report_to="none",
        remove_unused_columns=False,
    )

    trainer = DPOTrainer(
        model=model,
        ref_model=None,  # TRL automatically freezes reference adapter for PEFT
        peft_config=peft_config,
        args=dpo_config,
        train_dataset=train_dataset,
        processing_class=tokenizer,
    )

    _cast_trainable_fp32(trainer.model)

    print("\nStarting DPO training loop...")
    trainer.train()

    print(f"\nSaving DPO adapter to: {output_dir}")
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    if args.push_to_hub:
        push_dpo_adapter_to_hub(
            adapter_dir=output_dir,
            repo_id=args.hub_dpo_repo,
            base_model_id=args.base_model,
            sft_adapter=args.sft_adapter,
        )

    print("\n🎉 DPO Fine-Tuning Completed Successfully!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
