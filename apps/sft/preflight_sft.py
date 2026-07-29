#!/usr/bin/env python3
"""Pre-flight checks before a long SFT run.

Validates chat template rendering, assistant-only loss masks, and optional model load.

Usage (from apps/sft):

    uv run python preflight_sft.py
    uv run python preflight_sft.py --colab --load-model
    uv run python preflight_sft.py --adapter-dir ./qwen25-coder-7b-manim-ft
"""

from __future__ import annotations

import argparse
import sys

from chat_template import prepare_training_tokenizer, validate_training_template
from config import TrainingConfig, build_arg_parser
from data import format_trajectory_messages, log_token_length_stats
from model import load_model, load_tokenizer


def _sample_messages() -> list[dict]:
    sample = {
        "user_prompt": "Animate a circle.",
        "final_code": "class Scene(Scene):\n    def construct(self):\n        pass",
        "summary": "Fixed axes",
        "trajectory": [
            {
                "tool_name": "render",
                "input": "Scene().render()",
                "output": "Render failed: Axes not defined",
            },
            {
                "tool_name": "render",
                "input": "Scene().render()",
                "output": "ok",
            },
        ],
    }
    return format_trajectory_messages(sample)["messages"]


def _check_assistant_masks(tokenizer, messages: list[dict]) -> tuple[int, str]:
    processed = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        return_dict=True,
        return_assistant_tokens_mask=True,
    )
    input_ids = processed["input_ids"]
    assistant_masks = processed["assistant_masks"]
    mask_sum = sum(assistant_masks)
    masked_ids = [
        token_id
        for token_id, mask in zip(input_ids, assistant_masks, strict=False)
        if mask
    ]
    masked_text = tokenizer.decode(masked_ids)
    return mask_sum, masked_text


def _tool_call_in_mask(masked_text: str) -> bool:
    return (
        "<tool_call>" in masked_text
        or "<|tool_call>" in masked_text
        or "tool_call" in masked_text
    )


def run_preflight(
    config: TrainingConfig,
    *,
    load_model_smoke: bool = False,
    adapter_dir: str | None = None,
) -> int:
    print(f"Model: {config.model_id}")
    print(f"Attention: {config.attn_implementation}")
    print(f"4-bit: {config.use_4bit}")
    print(f"assistant_only_loss: {config.assistant_only_loss}")
    print(f"packing: {config.packing}")
    print(f"seq_len: {config.seq_len}")

    if adapter_dir:
        from pathlib import Path

        from model import load_adapter_tokenizer

        tokenizer = load_adapter_tokenizer(config, Path(adapter_dir))
        print(f"Tokenizer source: {adapter_dir}")
    else:
        tokenizer = load_tokenizer(config.model_id)

    config = prepare_training_tokenizer(tokenizer, config)
    validate_training_template(
        tokenizer, require_generation_markers=config.assistant_only_loss
    )

    messages = _sample_messages()
    rendered = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
    )
    print("\n--- Rendered chat template (sample) ---")
    preview = (
        rendered if len(rendered) <= 2000 else rendered[:2000] + "\n... [truncated]"
    )
    print(preview)

    from datasets import Dataset

    log_token_length_stats(
        tokenizer,
        Dataset.from_list([{"messages": messages}]),
        config.seq_len,
    )

    if config.assistant_only_loss:
        mask_sum, masked_text = _check_assistant_masks(tokenizer, messages)
        if mask_sum == 0:
            print("\nFAIL: assistant_masks are all zero")
            return 1
        if "Render failed: Axes not defined" in masked_text:
            print("\nFAIL: tool error text appears in assistant loss mask")
            print("masked:", repr(masked_text[:500]))
            return 1
        if not _tool_call_in_mask(masked_text):
            print("\nFAIL: tool_call tokens missing from assistant loss mask")
            print("masked:", repr(masked_text[:500]))
            return 1
        print(
            f"\nOK: assistant_masks ({mask_sum} tokens trained; "
            f"{len(messages)} message turns in sample)"
        )
        print("--- Assistant-masked decode (loss tokens) ---")
        print(
            masked_text
            if len(masked_text) <= 1500
            else masked_text[:1500] + "\n... [truncated]"
        )

    if load_model_smoke:
        print("\nLoading model smoke test...")
        try:
            model = load_model(config, for_inference=True)
            param_count = sum(p.numel() for p in model.parameters())
            print(f"OK: model loaded ({param_count:,} parameters)")
            del model
        except Exception as exc:
            print(f"\nFAIL: model load failed: {exc}", file=sys.stderr)
            return 1

    print("\nPreflight passed.")
    return 0


def main() -> int:
    base_parser = build_arg_parser()
    parser = argparse.ArgumentParser(
        parents=[base_parser],
        description=__doc__,
        conflict_handler="resolve",
    )
    parser.add_argument(
        "--load-model",
        action="store_true",
        help="Smoke-load the base model (requires GPU + HF_TOKEN)",
    )
    parser.add_argument(
        "--adapter-dir",
        default=None,
        help="Validate tokenizer saved with a trained adapter instead of base model",
    )
    args = parser.parse_args()
    config = TrainingConfig.from_cli(args)
    return run_preflight(
        config,
        load_model_smoke=args.load_model,
        adapter_dir=args.adapter_dir,
    )


if __name__ == "__main__":
    raise SystemExit(main())
