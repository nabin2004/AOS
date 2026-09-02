import os
import sys
from typing import Any
from pathlib import Path
from datasets import Dataset, concatenate_datasets, load_dataset

from config import TrainingConfig

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def _effective_num_proc(requested: int) -> int:
    """Enforce single process on Windows to prevent multiprocessing spawn deadlocks."""
    if sys.platform == "win32":
        return 1
    return max(1, requested)

# Native Hub chat corpora (parquet / DatasetDict), not raw JSONL paths.
_NATIVE_HF_REPOS = frozenset(
    {
        "nabin2004/manim-sft",
        "nabin2004/manim-sft-10k",
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
        p = Path(config.data_path)
        if not p.is_file():
            if "5k" in str(p):
                print(f"Local dataset {p} not found. Auto-curating 5k dataset now...")
                try:
                    from curate_sft_5k import curate_5k_dataset
                    curate_5k_dataset(p.parent)
                except Exception as exc:
                    print(f"WARNING: Auto-curation failed: {exc}")
            elif not p.is_file():
                raise FileNotFoundError(f"Specified dataset file not found: {p}")
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
    num_proc = _effective_num_proc(config.num_proc)
    ds = _load_raw_dataset(config)
    ds = ds.filter(_is_trainable, num_proc=num_proc)
    ds = ds.map(
        _normalize_messages,
        remove_columns=ds.column_names,
        num_proc=num_proc,
    )
    ds = _maybe_subsample(ds, config)

    if config.replay_ratio > 0.0 and config.replay_dataset:
        num_replay = int(len(ds) * config.replay_ratio)
        if num_replay > 0:
            print(
                f"Mixing {config.replay_ratio * 100:.0f}% replay buffer "
                f"({num_replay} rows from {config.replay_dataset})..."
            )
            try:
                if config.replay_dataset in _NATIVE_HF_REPOS:
                    raw_replay = load_dataset(config.replay_dataset, split="train")
                else:
                    raw_replay = load_dataset("json", data_files=config.replay_dataset, split="train")
                raw_replay = raw_replay.filter(_is_trainable, num_proc=num_proc)
                num_replay = min(num_replay, len(raw_replay))
                raw_replay = raw_replay.shuffle(seed=config.shuffle_seed).select(range(num_replay))
                replay_ds = raw_replay.map(
                    _normalize_messages,
                    remove_columns=raw_replay.column_names,
                    num_proc=num_proc,
                )
                ds = concatenate_datasets([ds, replay_ds]).shuffle(seed=config.shuffle_seed)
            except Exception as exc:
                print(f"WARNING: Failed to mix replay dataset ({exc})")

    print(f"Trainable rows (total): {len(ds)}")
    if len(ds) > 0:
        roles = [
            m.get("role")
            for m in (ds[0].get("messages") or [])
            if isinstance(m, dict)
        ]
        print(f"Sample roles: {roles}")
    return ds
