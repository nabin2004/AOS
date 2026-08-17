from __future__ import annotations

from typing import Any

from datasets import Dataset, load_dataset

from config import TrainingConfig

# Native Hub chat corpora (parquet / DatasetDict), not raw JSONL paths.
_NATIVE_HF_REPOS = frozenset(
    {
        "nabin2004/manim-sft",
        "nabin2004/educlaw-manim-sft",
    }
)


def native_sft_chat_repo(repo: str | None) -> bool:
    return bool(repo) and repo in _NATIVE_HF_REPOS


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

    # Trajectory / tool-trace rows only (AOS-Trajectories), not manim-sft chat.
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


def _load_raw_dataset(config: TrainingConfig) -> Dataset:
    """Load from local JSONL, native Hub datasets, or hf:// JSON paths."""
    if config.data_path is not None:
        path = str(config.data_path)
        print(f"Loading dataset from {path}")
        return load_dataset("json", data_files=path, split="train")

    repo = config.dataset_repo
    split = config.dataset_split
    if repo in _NATIVE_HF_REPOS:
        print(f"Loading native Hub dataset {repo} split={split}")
        try:
            return load_dataset(repo, split=split)
        except Exception as exc:
            print(f"WARNING: native load failed ({exc}); falling back to json files")

    path = resolve_data_files(config)
    print(f"Loading dataset from {path}")
    return load_dataset("json", data_files=path, split="train")


def _maybe_subsample(ds: Dataset, config: TrainingConfig) -> Dataset:
    max_samples = config.max_samples
    if max_samples is None or max_samples <= 0 or len(ds) <= max_samples:
        return ds
    print(
        f"Subsampling {max_samples} of {len(ds)} rows "
        f"(seed={config.shuffle_seed})"
    )
    return ds.shuffle(seed=config.shuffle_seed).select(range(max_samples))


def load_training_dataset(config: TrainingConfig) -> Dataset:
    ds = _load_raw_dataset(config)
    ds = ds.filter(_is_trainable, num_proc=config.num_proc)
    ds = ds.map(
        _normalize_messages,
        remove_columns=ds.column_names,
        num_proc=config.num_proc,
    )
    ds = _maybe_subsample(ds, config)
    print(f"Trainable rows: {len(ds)}")
    if len(ds) > 0:
        roles = [
            m.get("role")
            for m in (ds[0].get("messages") or [])
            if isinstance(m, dict)
        ]
        print(f"Sample roles: {roles}")
    return ds
