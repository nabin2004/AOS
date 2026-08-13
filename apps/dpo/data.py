from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from datasets import Dataset


def _messages_to_text(messages: list[dict[str, Any]], tokenizer) -> str:
    """Flatten chat messages with the model chat template (no generation prompt)."""
    # DPO expects prompt / chosen / rejected strings for many TRL versions.
    # Prefer tokenizer chat template when available.
    try:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )
    except Exception:
        parts: list[str] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content") or ""
            if msg.get("tool_calls"):
                content = content or json.dumps(msg["tool_calls"])
            parts.append(f"<|{role}|>\n{content}")
        return "\n".join(parts)


def _split_prompt_completion(
    messages: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Use first user turn as prompt boundary; rest is completion."""
    if not messages:
        return [], []
    # Prompt = everything up to and including first user message
    idx = 0
    for i, msg in enumerate(messages):
        if msg.get("role") == "user":
            idx = i
            break
    prompt_msgs = messages[: idx + 1]
    completion_msgs = messages[idx + 1 :]
    return prompt_msgs, completion_msgs


def load_preference_dataset(
    path: Path,
    tokenizer,
    *,
    limit: int | None = None,
) -> Dataset:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            chosen = (obj.get("chosen") or {}).get("messages") or []
            rejected = (obj.get("rejected") or {}).get("messages") or []
            if not chosen or not rejected:
                continue

            # Prefer shared prompt from chosen
            prompt_msgs, chosen_comp = _split_prompt_completion(chosen)
            _, rejected_comp = _split_prompt_completion(rejected)
            if not prompt_msgs:
                prompt_msgs = [{"role": "user", "content": obj.get("prompt") or ""}]

            prompt = _messages_to_text(prompt_msgs, tokenizer)
            chosen_text = _messages_to_text(chosen_comp or chosen, tokenizer)
            rejected_text = _messages_to_text(rejected_comp or rejected, tokenizer)
            rows.append(
                {
                    "prompt": prompt,
                    "chosen": chosen_text,
                    "rejected": rejected_text,
                }
            )
            if limit is not None and len(rows) >= limit:
                break

    if not rows:
        raise ValueError(f"No preference pairs loaded from {path}")
    return Dataset.from_list(rows)
