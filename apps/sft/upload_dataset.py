#!/usr/bin/env python3
"""Upload AOS SFT datasets to Hugging Face Hub.

Requires HF_TOKEN in the environment (write access). Never commit tokens.

Usage (from apps/sft):

    export HF_TOKEN=hf_...
    uv run python upload_dataset.py
    uv run python upload_dataset.py --repo-id nabin2004/AOS-Trajectories
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from huggingface_hub import HfApi, get_token

SFT_ROOT = Path(__file__).resolve().parent
AGENTS_ROOT = SFT_ROOT.parent / "agents"
DEFAULT_REPO_ID = "nabin2004/AOS-Trajectories"
DEFAULT_TRAJECTORIES = AGENTS_ROOT / "training_data" / "trajectories.jsonl"
DEFAULT_TOOL_TRACE_DIR = AGENTS_ROOT / "export_traces" / "coder_sft"
DATASET_CARD = SFT_ROOT / "dataset_card.md"


def _require_token() -> str:
    token = os.environ.get("HF_TOKEN", "").strip() or get_token()
    if not token:
        print(
            "ERROR: Set HF_TOKEN or run `huggingface-cli login` (write token required).",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def _upload_mapping(
    api: HfApi,
    repo_id: str,
    local_path: Path,
    hub_path: str,
    token: str,
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


def upload_dataset(
    repo_id: str,
    trajectories_path: Path,
    tool_trace_dir: Path,
    token: str,
) -> None:
    api = HfApi()
    api.create_repo(repo_id, repo_type="dataset", exist_ok=True, token=token)

    _upload_mapping(api, repo_id, trajectories_path, "trajectories.jsonl", token)
    _upload_mapping(
        api,
        repo_id,
        tool_trace_dir / "tool_trace.train.jsonl",
        "tool_trace/train.jsonl",
        token,
    )
    _upload_mapping(
        api,
        repo_id,
        tool_trace_dir / "tool_trace.val.jsonl",
        "tool_trace/val.jsonl",
        token,
    )
    _upload_mapping(
        api,
        repo_id,
        tool_trace_dir / "metadata.jsonl",
        "metadata.jsonl",
        token,
    )
    _upload_mapping(api, repo_id, DATASET_CARD, "README.md", token)

    print(f"Done: https://huggingface.co/datasets/{repo_id}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Upload AOS SFT data to Hugging Face")
    parser.add_argument(
        "--repo-id",
        default=DEFAULT_REPO_ID,
        help=f"HF dataset repo id (default: {DEFAULT_REPO_ID})",
    )
    parser.add_argument(
        "--trajectories-path",
        type=Path,
        default=DEFAULT_TRAJECTORIES,
        help="Local trajectories.jsonl",
    )
    parser.add_argument(
        "--tool-trace-dir",
        type=Path,
        default=DEFAULT_TOOL_TRACE_DIR,
        help="Directory with tool_trace.*.jsonl exports",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    token = _require_token()
    upload_dataset(
        repo_id=args.repo_id,
        trajectories_path=args.trajectories_path.resolve(),
        tool_trace_dir=args.tool_trace_dir.resolve(),
        token=token,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
