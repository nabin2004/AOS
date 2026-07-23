from __future__ import annotations

from typing import Any

from datasets import Dataset, load_dataset

from config import TrainingConfig


def resolve_data_files(config: TrainingConfig) -> str:
    """Return a path or hf:// URL for load_dataset."""
    if config.data_path is not None:
        return str(config.data_path)
    return f"hf://datasets/{config.dataset_repo}/{config.dataset_file}"


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


def load_training_dataset(config: TrainingConfig) -> Dataset:
    data_files = resolve_data_files(config)
    dataset = load_dataset("json", data_files=data_files, split="train")
    dataset = dataset.filter(_is_trainable_record, num_proc=config.num_proc)

    return dataset.map(
        format_trajectory_messages,
        remove_columns=dataset.column_names,
        num_proc=config.num_proc,
    )
