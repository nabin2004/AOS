#!/usr/bin/env python3
"""Merge a Gemma 4 LoRA adapter into a bf16 base model for deployment.

Never merge into the 4-bit training checkpoint — reload bf16 on CPU, merge, then
quantize separately (GGUF / AWQ / vLLM) if needed.

Usage (from apps/sft):

    uv run python merge_adapter.py \\
      --adapter-dir ./gemma4-manim-ft \\
      --output-dir ./gemma4-manim-merged

    uv run python merge_adapter.py \\
      --adapter-dir /content/drive/MyDrive/gemma4-manim-ft \\
      --output-dir /content/drive/MyDrive/gemma4-manim-merged
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoTokenizer

from chat_template import prepare_training_tokenizer, validate_training_template
from config import TrainingConfig
from model import _load_pretrained_gemma4, _hub_token


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--adapter-dir",
        type=Path,
        required=True,
        help="LoRA adapter directory saved by run.py",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for merged bf16 weights + tokenizer",
    )
    parser.add_argument(
        "--model-id",
        default="google/gemma-4-E2B-it",
        help="Base model id (must match adapter training run)",
    )
    return parser


def merge_adapter(
    adapter_dir: Path,
    output_dir: Path,
    model_id: str,
) -> None:
    if not adapter_dir.is_dir():
        raise FileNotFoundError(f"Adapter directory not found: {adapter_dir}")
    if not (adapter_dir / "adapter_config.json").is_file():
        raise FileNotFoundError(f"No adapter_config.json in {adapter_dir}")

    token = _hub_token()
    print(f"Loading base model {model_id} in bf16 on CPU...")
    base = _load_pretrained_gemma4(
        model_id,
        dtype=torch.bfloat16,
        device_map="cpu",
        attn_implementation="eager",
        token=token,
    )

    print(f"Attaching adapter from {adapter_dir}...")
    model = PeftModel.from_pretrained(base, str(adapter_dir), token=token)
    print("Merging LoRA weights into base...")
    merged = model.merge_and_unload()

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Saving merged model to {output_dir}...")
    merged.save_pretrained(str(output_dir), safe_serialization=True)

    tokenizer_source = (
        adapter_dir if (adapter_dir / "tokenizer_config.json").is_file() else model_id
    )
    tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_source), token=token)
    config = prepare_training_tokenizer(tokenizer, TrainingConfig(model_id=model_id))
    validate_training_template(
        tokenizer, require_generation_markers=config.assistant_only_loss
    )
    tokenizer.save_pretrained(str(output_dir))
    print("Merge complete.")


def main() -> int:
    args = build_parser().parse_args()
    try:
        merge_adapter(
            args.adapter_dir.resolve(), args.output_dir.resolve(), args.model_id
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
