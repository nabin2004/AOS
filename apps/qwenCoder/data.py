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

QWEN_ROOT = Path(__file__).resolve().parent

# Native Hub chat corpora (parquet / DatasetDict), not raw JSONL paths.
_NATIVE_HF_REPOS = frozenset(
    {
        "nabin2004/manim-sft",
        "nabin2004/manim-sft-10k",
        "nabin2004/educlaw-manim-sft",
        "nabin2004/manim-aos-5k400",
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

    # Check for local file in QWEN_ROOT / repo_basename / train.jsonl
    repo_slug = repo.split("/")[-1]
    local_jsonl = QWEN_ROOT / repo_slug / "train.jsonl"
    if local_jsonl.is_file():
        print(f"Loading local dataset from {local_jsonl}")
        return load_dataset("json", data_files=str(local_jsonl), split="train")

    if repo in _NATIVE_HF_REPOS:
        print(f"Loading native Hub dataset {repo} split={split}")
        try:
            return load_dataset(repo, split=split)
        except Exception as exc:
            print(f"WARNING: native load failed ({exc}); trying fallback")

    try:
        print(f"Loading dataset {repo} split={split}")
        return load_dataset(repo, split=split)
    except Exception:
        path = resolve_data_files(config)
        print(f"Loading dataset from {path}")
        return load_dataset("json", data_files=path, split="train")


def _is_trajectory_sample(sample: dict[str, Any]) -> bool:
    """Identify if a sample is part of the 400 high-quality AOS agent trajectories."""
    if sample.get("bucket") == "aos_agent_trajectories":
        return True
    if sample.get("source") in ("prompts_andrej_400", "tool_trace"):
        return True
    if "extra" in sample and isinstance(sample["extra"], dict):
        if "trajectory_index" in sample["extra"]:
            return True
    return bool(sample.get("trajectory"))


def _maybe_subsample(ds: Dataset, config: TrainingConfig) -> Dataset:
    max_samples = config.max_samples
    if max_samples is None or max_samples <= 0 or len(ds) <= max_samples:
        return ds
    print(
        f"Subsampling {max_samples} of {len(ds)} rows "
        f"(seed={config.shuffle_seed})"
    )
    return ds.shuffle(seed=config.shuffle_seed).select(range(max_samples))


def _maybe_mix_replay(ds: Dataset, config: TrainingConfig, num_proc: int) -> Dataset:
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
    return ds


def load_training_and_eval_datasets(config: TrainingConfig) -> tuple[Dataset, Dataset | None]:
    num_proc = _effective_num_proc(config.num_proc)
    raw_ds = _load_raw_dataset(config)
    raw_ds = raw_ds.filter(_is_trainable, num_proc=num_proc)

    val_split = config.val_split
    if val_split <= 0.0 or len(raw_ds) < 20:
        ds = raw_ds.map(
            _normalize_messages,
            remove_columns=raw_ds.column_names,
            num_proc=num_proc,
        )
        ds = _maybe_subsample(ds, config)
        ds = _maybe_mix_replay(ds, config, num_proc)
        print(f"Trainable rows (total): {len(ds)}")
        return ds, None

    # Separate high-quality trajectories (which must remain 100% in train)
    trajectory_mask = [_is_trajectory_sample(sample) for sample in raw_ds]
    traj_indices = [i for i, is_traj in enumerate(trajectory_mask) if is_traj]
    other_indices = [i for i, is_traj in enumerate(trajectory_mask) if not is_traj]

    print(
        f"Dataset split: {len(traj_indices)} high-quality trajectory rows protected in train, "
        f"{len(other_indices)} standard rows eligible for eval split."
    )

    other_ds = raw_ds.select(other_indices).shuffle(seed=config.shuffle_seed)
    num_eval = max(1, int(len(other_ds) * val_split))
    eval_raw = other_ds.select(range(num_eval))
    train_other_raw = other_ds.select(range(num_eval, len(other_ds)))

    if traj_indices:
        traj_raw = raw_ds.select(traj_indices)
        train_raw = concatenate_datasets([traj_raw, train_other_raw]).shuffle(seed=config.shuffle_seed)
    else:
        train_raw = train_other_raw

    train_ds = train_raw.map(
        _normalize_messages,
        remove_columns=train_raw.column_names,
        num_proc=num_proc,
    )
    eval_ds = eval_raw.map(
        _normalize_messages,
        remove_columns=eval_raw.column_names,
        num_proc=num_proc,
    )

    train_ds = _maybe_subsample(train_ds, config)
    train_ds = _maybe_mix_replay(train_ds, config, num_proc)

    print(
        f"✔ Final dataset split complete: Train rows={len(train_ds)} "
        f"(100% of trajectory samples protected), Eval rows={len(eval_ds)}"
    )
    return train_ds, eval_ds


def load_training_dataset(config: TrainingConfig) -> Dataset:
    train_ds, _ = load_training_and_eval_datasets(config)
    return train_ds
