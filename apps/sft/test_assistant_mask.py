#!/usr/bin/env python3
"""Smoke test: Gemma 4 assistant-only loss masks tool errors but not tool calls."""

from __future__ import annotations


from chat_template import prepare_training_tokenizer, validate_training_template
from config import TrainingConfig
from data import format_trajectory_messages
from model import load_tokenizer


def _masked_text(tokenizer, input_ids: list[int], assistant_masks: list[int]) -> str:
    masked_ids = [
        token_id
        for token_id, mask in zip(input_ids, assistant_masks, strict=False)
        if mask
    ]
    return tokenizer.decode(masked_ids)


def main() -> int:
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
    formatted = format_trajectory_messages(sample)
    messages = formatted["messages"]

    tokenizer = load_tokenizer(TrainingConfig().model_id)
    config = prepare_training_tokenizer(tokenizer, TrainingConfig())
    assert config.assistant_only_loss is True, "assistant_only_loss should stay enabled"
    validate_training_template(tokenizer, require_generation_markers=True)

    processed = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        return_dict=True,
        return_assistant_tokens_mask=True,
    )
    input_ids = processed["input_ids"]
    assistant_masks = processed["assistant_masks"]
    mask_sum = sum(assistant_masks)

    if mask_sum == 0:
        print("FAIL: assistant_masks are all zero")
        return 1

    masked = _masked_text(tokenizer, input_ids, assistant_masks)
    full = tokenizer.decode(input_ids)

    if "Render failed: Axes not defined" in masked:
        print("FAIL: tool error text appears in assistant loss mask")
        print("masked:", repr(masked))
        return 1

    if "<|tool_call>" not in masked and "tool_call" not in masked:
        print("FAIL: tool_call tokens missing from assistant loss mask")
        print("masked:", repr(masked))
        return 1

    if "Render failed: Axes not defined" not in full:
        print("FAIL: tool error missing from full sequence (model cannot see context)")
        return 1

    print("OK: assistant_only_loss masking")
    print(f"  masked tokens: {mask_sum} / {len(input_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
