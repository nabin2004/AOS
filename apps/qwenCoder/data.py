from __future__ import annotations

from typing import Any

from datasets import Dataset, load_dataset

from config import TrainingConfig


def resolve_data_files(config: TrainingConfig) -> str:
    if config.data_path is not None:
        return str(config.data_path)
    return f"hf://datasets/{config.dataset_repo}/{config.dataset_file}"


def _normalize_messages(sample: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    messages = sample.get("messages")
    if isinstance(messages, list) and messages:
        return {"messages": messages}

    chosen = sample.get("chosen")
    if isinstance(chosen, dict) and isinstance(chosen.get("messages"), list):
        return {"messages": chosen["messages"]}

    prompt = sample.get("prompt") or sample.get("user_prompt") or ""
    final_code = sample.get("final_code") or ""
    out: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
    for i, step in enumerate(sample.get("trajectory") or []):
        call_id = f"call_{i}"
        tool_name = step.get("tool_name") or "run_code"
        out.append(
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
        out.append(
            {
                "role": "tool",
                "tool_call_id": call_id,
                "name": tool_name,
                "content": step.get("output", ""),
            }
        )
    if final_code:
        out.append({"role": "assistant", "content": final_code})
    return {"messages": out}


def _is_trainable(sample: dict[str, Any]) -> bool:
    if sample.get("messages"):
        return True
    if sample.get("chosen"):
        return True
    if sample.get("success") is False:
        return False
    return bool(sample.get("final_code") or sample.get("trajectory"))


def load_training_dataset(config: TrainingConfig) -> Dataset:
    path = resolve_data_files(config)
    print(f"Loading dataset from {path}")
    ds = load_dataset("json", data_files=path, split="train")
    ds = ds.filter(_is_trainable)
    ds = ds.map(_normalize_messages)
    # SFTTrainer expects a messages column
    drop = [c for c in ds.column_names if c != "messages"]
    if drop:
        ds = ds.remove_columns(drop)
    print(f"Trainable rows: {len(ds)}")
    return ds
