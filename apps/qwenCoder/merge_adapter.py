#!/usr/bin/env python3
"""Merge a Qwen LoRA adapter into bf16 base weights.

Usage (from apps/qwenCoder):

    uv run python merge_adapter.py \\
      --adapter-dir ./qwen2.5-coder-7b-manim-ft \\
      --output-dir ./qwen2.5-coder-7b-manim-merged
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from hub_upload import push_model_folder, require_token
from identity import BASE_MODEL_ID, HUB_MERGED_REPO


def _hub_token() -> str | None:
    return os.environ.get("HF_TOKEN", "").strip() or None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--adapter-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-id", default=BASE_MODEL_ID)
    parser.add_argument("--push-to-hub", action="store_true")
    parser.add_argument("--hub-repo-id", default=HUB_MERGED_REPO)
    parser.add_argument("--hub-private", action="store_true")
    args = parser.parse_args()

    adapter_dir = args.adapter_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not adapter_dir.is_dir():
        print(f"ERROR: adapter not found: {adapter_dir}")
        return 1

    print(f"Loading base {args.model_id} (bf16/CPU-friendly)...")
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_id, trust_remote_code=True, token=_hub_token()
    )
    base = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        torch_dtype=torch.bfloat16,
        device_map="cpu",
        trust_remote_code=True,
        token=_hub_token(),
    )
    print(f"Loading adapter from {adapter_dir}...")
    model = PeftModel.from_pretrained(base, str(adapter_dir))
    print("Merging...")
    model = model.merge_and_unload()

    output_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    print(f"Merged model saved to {output_dir}")

    if args.push_to_hub:
        token = require_token()
        push_model_folder(
            output_dir,
            args.hub_repo_id,
            token,
            private=args.hub_private,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
