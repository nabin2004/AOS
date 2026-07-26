#!/usr/bin/env python3
"""Merge a Gemma 4 LoRA adapter into a bf16 base model for deployment.

Never merge into the 4-bit training checkpoint — reload bf16 on CPU, merge, then
quantize separately (GGUF / AWQ / vLLM) if needed.

Usage (from apps/sft):

    uv run python merge_adapter.py \\
      --adapter-dir ./gemma4-manim-ft \\
      --output-dir ./gemma4-manim-merged

    export HF_TOKEN=hf_...
    uv run python merge_adapter.py \\
      --adapter-dir ./gemma4-manim-ft \\
      --output-dir ./gemma4-manim-merged \\
      --push-to-hub
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoTokenizer

from chat_template import prepare_training_tokenizer, validate_training_template
from config import TrainingConfig
from hub_upload import push_model_folder, require_token
from model import _load_pretrained_gemma4, _hub_token

SFT_ROOT = Path(__file__).resolve().parent
DEFAULT_HUB_REPO_ID = "nabin2004/AOS-gemma4-manim-merged"
MERGED_MODEL_CARD = SFT_ROOT / "merged_model_card.md"


@dataclass(frozen=True)
class MergeConfig:
    adapter_dir: Path
    output_dir: Path
    model_id: str
    push_to_hub: bool
    hub_repo_id: str
    hub_private: bool
    hub_revision: str | None


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
    parser.add_argument(
        "--push-to-hub",
        action="store_true",
        help="Upload merged weights to Hugging Face Hub after merge",
    )
    parser.add_argument(
        "--hub-repo-id",
        default=DEFAULT_HUB_REPO_ID,
        help=f"HF model repo id (default: {DEFAULT_HUB_REPO_ID})",
    )
    parser.add_argument(
        "--hub-private",
        action="store_true",
        help="Create/upload as a private model repo",
    )
    parser.add_argument(
        "--hub-revision",
        default=None,
        help="Optional branch or tag name for the Hub upload",
    )
    return parser


def merge_adapter(config: MergeConfig) -> None:
    adapter_dir = config.adapter_dir
    output_dir = config.output_dir
    model_id = config.model_id

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
    training_config = prepare_training_tokenizer(
        tokenizer, TrainingConfig(model_id=model_id)
    )
    validate_training_template(
        tokenizer, require_generation_markers=training_config.assistant_only_loss
    )
    tokenizer.save_pretrained(str(output_dir))
    print("Merge complete.")

    if config.push_to_hub:
        hub_token = require_token()
        push_model_folder(
            output_dir,
            config.hub_repo_id,
            hub_token,
            readme=MERGED_MODEL_CARD,
            private=config.hub_private,
            revision=config.hub_revision,
        )


def main() -> int:
    args = build_parser().parse_args()
    config = MergeConfig(
        adapter_dir=args.adapter_dir.resolve(),
        output_dir=args.output_dir.resolve(),
        model_id=args.model_id,
        push_to_hub=args.push_to_hub,
        hub_repo_id=args.hub_repo_id,
        hub_private=args.hub_private,
        hub_revision=args.hub_revision,
    )
    try:
        merge_adapter(config)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
