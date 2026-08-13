#!/usr/bin/env python3
"""Upload Qwen trajectory dataset (raw + tool_trace + preference) to Hugging Face.

Usage (from apps/qwenCoder):

    export HF_TOKEN=hf_...
    uv run python upload_dataset.py
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from huggingface_hub import HfApi, get_token

QWEN_ROOT = Path(__file__).resolve().parent
AGENTS_ROOT = QWEN_ROOT.parent / "agents"
DEFAULT_REPO_ID = "nabin2004/AOS-Qwen-Trajectories"
DEFAULT_TRAJECTORIES = AGENTS_ROOT / "training_data" / "trajectories.jsonl"
DEFAULT_TOOL_TRACE_DIR = AGENTS_ROOT / "export_traces" / "coder_sft"
DEFAULT_PREF_DIR = AGENTS_ROOT / "export_traces" / "coder_sft" / "preference"
DATASET_CARD = QWEN_ROOT / "dataset_card.md"


def _require_token() -> str:
    token = os.environ.get("HF_TOKEN", "").strip() or get_token()
    if not token:
        print(
            "ERROR: Set HF_TOKEN or run `huggingface-cli login`.",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def _upload_file(
    api: HfApi, repo_id: str, local_path: Path, hub_path: str, token: str
) -> None:
    if not local_path.is_file():
        print(f"SKIP (missing): {local_path}", file=sys.stderr)
        return
    print(f"Uploading {local_path} -> {repo_id}/{hub_path}")
    api.upload_file(
        path_or_fileobj=str(local_path),
        path_in_repo=hub_path,
        repo_id=repo_id,
        repo_type="dataset",
        token=token,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--trajectories", type=Path, default=DEFAULT_TRAJECTORIES)
    parser.add_argument("--tool-trace-dir", type=Path, default=DEFAULT_TOOL_TRACE_DIR)
    parser.add_argument("--preference-dir", type=Path, default=DEFAULT_PREF_DIR)
    args = parser.parse_args()

    token = _require_token()
    api = HfApi()
    api.create_repo(args.repo_id, repo_type="dataset", exist_ok=True, token=token)

    _upload_file(api, args.repo_id, args.trajectories, "trajectories.jsonl", token)
    for name, hub in (
        ("tool_trace.train.jsonl", "tool_trace/train.jsonl"),
        ("tool_trace.val.jsonl", "tool_trace/val.jsonl"),
        ("tool_trace.jsonl", "tool_trace/train.jsonl"),
        ("metadata.jsonl", "metadata.jsonl"),
    ):
        _upload_file(api, args.repo_id, args.tool_trace_dir / name, hub, token)

    for name, hub in (
        ("train.jsonl", "preference/train.jsonl"),
        ("val.jsonl", "preference/val.jsonl"),
    ):
        _upload_file(api, args.repo_id, args.preference_dir / name, hub, token)

    if DATASET_CARD.is_file():
        _upload_file(api, args.repo_id, DATASET_CARD, "README.md", token)

    print(f"Done: https://huggingface.co/datasets/{args.repo_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
