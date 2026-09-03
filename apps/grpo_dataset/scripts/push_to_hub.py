#!/usr/bin/env python3
"""Push ManiBench GRPO dataset (problems, splits, metadata, and README) to Hugging Face Hub.

Target Repository: nabin2004/manibench-grpo
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from huggingface_hub import HfApi, get_token
except ImportError:
    HfApi = None
    get_token = None

SCRIPT_DIR = Path(__file__).resolve().parent
GRPO_DATASET_DIR = SCRIPT_DIR.parent
DATA_DIR = GRPO_DATASET_DIR / "data"
HF_README = GRPO_DATASET_DIR / "HF_README.md"
CURATED_PATH = SCRIPT_DIR / "curated_scenes.json"

DEFAULT_REPO_ID = "nabin2004/manibench-grpo"


def push_dataset(repo_id: str, token: str | None = None) -> None:
    if HfApi is None:
        raise ImportError("huggingface-hub is required (`uv add huggingface-hub`).")

    resolved_token = token or os.environ.get("HF_TOKEN") or (get_token() if get_token else None)
    if not resolved_token:
        raise ValueError("HF_TOKEN environment variable or token parameter is required.")

    api = HfApi(token=resolved_token)

    print(f"1. Creating dataset repository on Hugging Face: {repo_id}")
    api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, token=resolved_token)

    # 2. Upload README
    if HF_README.is_file():
        print(f"2. Uploading {HF_README.name} -> README.md")
        api.upload_file(
            path_or_fileobj=str(HF_README),
            path_in_repo="README.md",
            repo_id=repo_id,
            repo_type="dataset",
            token=resolved_token,
        )

    # 3. Upload curated_scenes.json
    if CURATED_PATH.is_file():
        print(f"3. Uploading {CURATED_PATH.name} -> scripts/curated_scenes.json")
        api.upload_file(
            path_or_fileobj=str(CURATED_PATH),
            path_in_repo="scripts/curated_scenes.json",
            repo_id=repo_id,
            repo_type="dataset",
            token=resolved_token,
        )

    # 4. Upload data directory (problems, splits, reference_index.json)
    if DATA_DIR.is_dir():
        print(f"4. Uploading folder {DATA_DIR} -> data/")
        api.upload_folder(
            folder_path=str(DATA_DIR),
            path_in_repo="data",
            repo_id=repo_id,
            repo_type="dataset",
            token=resolved_token,
        )

    print(f"\nSuccessfully published ManiBench GRPO dataset to: https://huggingface.co/datasets/{repo_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Push ManiBench GRPO dataset to Hugging Face Hub")
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID, help=f"HF dataset repo ID (default: {DEFAULT_REPO_ID})")
    parser.add_argument("--token", help="HF API token")
    args = parser.parse_args()

    try:
        push_dataset(repo_id=args.repo_id, token=args.token)
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
