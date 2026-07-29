from __future__ import annotations

import json
import statistics
from typing import Any

from datasets import Dataset, load_dataset
from transformers import PreTrainedTokenizerBase

from codemode_contract import messages_violate_codemode
from config import TrainingConfig


def resolve_data_files(config: TrainingConfig) -> str:
    """Return a path or hf:// URL for load_dataset."""
    if config.data_path is not None:
        return str(config.data_path)
    return f"hf://datasets/{config.dataset_repo}/{config.dataset_file}"


def _normalize_arguments(arguments: Any) -> dict[str, Any]:
    """Ensure tool-call arguments are a JSON object (mapping), not a string."""
    if arguments is None:
        return {}
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        text = arguments.strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"tool_calls[].function.arguments is not valid JSON: {exc}"
            ) from exc
        if isinstance(parsed, dict):
            return parsed
        return {"input": parsed}
    raise ValueError(
        f"Unsupported tool arguments type: {type(arguments).__name__}"
    )


def normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize OpenAI-style messages for chat-template rendering."""
    normalized: list[dict[str, Any]] = []
    for message in messages:
        msg = dict(message)
        role = msg.get("role")
        if role == "assistant":
            if msg.get("content") is None:
                msg["content"] = ""
            tool_calls = msg.get("tool_calls")
            if isinstance(tool_calls, list):
                fixed_calls: list[dict[str, Any]] = []
                for call in tool_calls:
                    call_copy = dict(call)
                    fn = call_copy.get("function")
                    if isinstance(fn, dict):
                        fn_copy = dict(fn)
                        fn_copy["arguments"] = _normalize_arguments(
                            fn_copy.get("arguments")
                        )
                        call_copy["function"] = fn_copy
                    fixed_calls.append(call_copy)
                msg["tool_calls"] = fixed_calls
        elif role == "tool" and msg.get("content") is None:
            msg["content"] = ""
        normalized.append(msg)
    return normalized


def format_trajectory_messages(
    sample: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Convert an agent trajectory record into OpenAI-style chat messages."""
    existing = sample.get("messages")
    if isinstance(existing, list) and existing:
        return {"messages": normalize_messages(existing)}

    prompt = sample.get("prompt") or sample.get("user_prompt") or ""
    narration = sample.get("narration") or sample.get("summary", "")
    final_code = sample.get("final_code") or ""

    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

    for i, step in enumerate(sample.get("trajectory") or []):
        tool_name = step.get("tool_name") or "execute"
        call_id = f"call_{i}"
        messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": {"input": step.get("input", "")},
                        },
                    }
                ],
            }
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call_id,
                "name": tool_name,
                "content": step.get("output", "") or "",
            }
        )

    final_content = f"```python\n{final_code}\n```\n\nNarration: {narration}"
    messages.append({"role": "assistant", "content": final_content})

    return {"messages": normalize_messages(messages)}


def _is_trainable_record(sample: dict[str, Any]) -> bool:
    if sample.get("messages"):
        return True
    if sample.get("success") is False:
        return False
    final_code = sample.get("final_code")
    return bool(final_code and str(final_code).strip())


def _passes_codemode_contract(sample: dict[str, Any]) -> bool:
    messages = sample.get("messages")
    if isinstance(messages, list):
        return not messages_violate_codemode(messages)
    return True


def load_training_dataset(config: TrainingConfig) -> Dataset:
    data_files = resolve_data_files(config)
    dataset = load_dataset(
        "json",
        data_files=data_files,
        split="train",
        keep_in_memory=True,
    )
    dataset = dataset.filter(
        _is_trainable_record,
        num_proc=config.num_proc,
        load_from_cache_file=False,
    )
    dataset = dataset.map(
        format_trajectory_messages,
        remove_columns=dataset.column_names,
        num_proc=config.num_proc,
        load_from_cache_file=False,
    )
    before = len(dataset)
    dataset = dataset.filter(
        _passes_codemode_contract,
        num_proc=config.num_proc,
        load_from_cache_file=False,
    )
    dropped = before - len(dataset)
    if dropped:
        print(
            f"Dropped {dropped} rows with CodeMode star-import violations "
            f"({len(dataset)} remain)"
        )
    return dataset


def log_token_length_stats(
    tokenizer: PreTrainedTokenizerBase,
    dataset: Dataset,
    seq_len: int,
    *,
    max_samples: int = 256,
) -> None:
    """Log min/median/p95/max token lengths and how many exceed seq_len."""
    n = min(len(dataset), max_samples)
    if n == 0:
        print("Token length stats: empty dataset")
        return

    lengths: list[int] = []
    for i in range(n):
        messages = dataset[i]["messages"]
        processed = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            return_dict=True,
            add_generation_prompt=False,
        )
        ids = processed["input_ids"]
        lengths.append(len(ids))

    lengths_sorted = sorted(lengths)
    p95_idx = min(len(lengths_sorted) - 1, int(0.95 * (len(lengths_sorted) - 1)))
    over = sum(1 for length in lengths if length > seq_len)
    print(
        "Token length stats "
        f"(n={n}{'/' + str(len(dataset)) if n < len(dataset) else ''}): "
        f"min={min(lengths)} median={statistics.median(lengths):.0f} "
        f"p95={lengths_sorted[p95_idx]} max={max(lengths)} "
        f"over_seq_len({seq_len})={over}"
    )
    if over:
        print(
            f"WARNING: {over}/{n} sampled trajectories exceed seq_len={seq_len}. "
            "With packing=False they will be truncated; raise --seq-len if VRAM allows."
        )
