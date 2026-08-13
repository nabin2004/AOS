#!/usr/bin/env python3
"""Preflight checks for Qwen2.5-Coder tool chat template + Manim SFT readiness."""

from __future__ import annotations

import argparse
import sys

from identity import BASE_MODEL_ID
from model import load_tokenizer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-id", default=BASE_MODEL_ID)
    args = parser.parse_args()

    tokenizer = load_tokenizer(args.model_id)
    template = getattr(tokenizer, "chat_template", None) or ""
    if not template:
        print("ERROR: tokenizer has no chat_template", file=sys.stderr)
        return 1

    markers = ("<|im_start|>", "<tool_call>", "<tools>")
    missing = [m for m in markers if m not in template]
    if missing:
        print(f"ERROR: chat_template missing markers: {missing}", file=sys.stderr)
        return 1

    tools = [
        {
            "type": "function",
            "function": {
                "name": "run_code",
                "description": "Execute CodeMode Python",
                "parameters": {
                    "type": "object",
                    "properties": {"code": {"type": "string"}},
                    "required": ["code"],
                },
            },
        }
    ]
    messages = [
        {"role": "system", "content": "You are AOS Manim coder."},
        {"role": "user", "content": "Animate Euler's formula."},
    ]
    rendered = tokenizer.apply_chat_template(
        messages,
        tools=tools,
        tokenize=False,
        add_generation_prompt=True,
    )
    for needle in ("run_code", "<tools>", "<|im_start|>assistant"):
        if needle not in rendered:
            print(f"ERROR: rendered prompt missing {needle!r}", file=sys.stderr)
            print(rendered[:2000], file=sys.stderr)
            return 1

    print(f"OK: {args.model_id} tool chat template looks ready")
    print(f"Rendered preview ({len(rendered)} chars):")
    print(rendered[:800])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
