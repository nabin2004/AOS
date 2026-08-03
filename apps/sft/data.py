from __future__ import annotations

from typing import Any

from datasets import Dataset, load_dataset

from codemode_contract import messages_violate_codemode
from config import TrainingConfig


def resolve_data_files(config: TrainingConfig) -> str:
    """Return a path or hf:// URL for load_dataset."""
    if config.data_path is not None:
        return str(config.data_path)
    return f"hf://datasets/{config.dataset_repo}/{config.dataset_file}"


def extract_user_prompt(sample: dict[str, Any]) -> str:
    """Return the user turn from a chat row or legacy trajectory record."""
    messages = sample.get("messages")
    if isinstance(messages, list):
        for msg in messages:
            if msg.get("role") == "user" and msg.get("content"):
                return str(msg["content"]).strip()
    return str(sample.get("user_prompt") or sample.get("prompt") or "").strip()


def format_trajectory_messages(
    sample: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Convert an agent trajectory record into Gemma-4-compatible messages."""
    existing = sample.get("messages")
    if isinstance(existing, list) and existing:
        return {"messages": existing}

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
                "content": None,
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
                "content": step.get("output", ""),
            }
        )

    final_content = f"```python\n{final_code}\n```\n\nNarration: {narration}"
    messages.append({"role": "assistant", "content": final_content})

    return {"messages": messages}


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


def _load_raw_dataset(config: TrainingConfig) -> Dataset:
    """Load the configured dataset from a local path or Hugging Face."""
    if config.data_path is not None:
        return load_dataset(
            "json", data_files=str(config.data_path), split="train"
        )
    if config.dataset_repo == "nabin2004/manim-sft":
        try:
            return load_dataset(config.dataset_repo, split="train")
        except Exception:
            pass
    data_files = resolve_data_files(config)
    return load_dataset("json", data_files=data_files, split="train")


def load_training_dataset(config: TrainingConfig) -> Dataset:
    dataset = _load_raw_dataset(config)
    dataset = dataset.filter(_is_trainable_record, num_proc=config.num_proc)
    dataset = dataset.map(
        format_trajectory_messages,
        remove_columns=dataset.column_names,
        num_proc=config.num_proc,
    )
    before = len(dataset)
    dataset = dataset.filter(_passes_codemode_contract, num_proc=config.num_proc)
    dropped = before - len(dataset)
    if dropped:
        print(
            f"Dropped {dropped} rows with CodeMode star-import violations ({len(dataset)} remain)"
        )
    return dataset
