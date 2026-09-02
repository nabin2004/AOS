#!/usr/bin/env python3
"""Upload AOS Narrated Manim Voiceover Dataset to Hugging Face Hub.

Requires HF_TOKEN in the environment (write access).

Usage:
    export HF_TOKEN=hf_...
    uv run python upload_narrated_dataset.py --repo-id nabin2004/AOS-Narrated-Manim-400
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

try:
    from huggingface_hub import HfApi, get_token
except ImportError:
    HfApi = None
    get_token = None

SFT_ROOT = Path(__file__).resolve().parent
AGENTS_ROOT = SFT_ROOT.parent / "agents"
REPO_ROOT = SFT_ROOT.parent.parent
DEFAULT_REPO_ID = "nabin2004/AOS-Narrated-Manim-400"
DEFAULT_DATASET_FILE = SFT_ROOT / "dataset_narrated" / "manim_narrated_400.jsonl"


def init_environment() -> None:
    """Auto-load environment variables from .env files in sft, agents, or repo root."""
    if load_dotenv:
        for env_path in (
            REPO_ROOT / ".env",
            AGENTS_ROOT / ".env",
            SFT_ROOT / ".env",
            Path.cwd() / ".env",
        ):
            if env_path.is_file():
                load_dotenv(env_path, override=False)


def generate_dataset_card(repo_id: str, sample_count: int) -> str:
    """Generate Markdown dataset card for Hugging Face Hub."""
    return f"""---
license: mit
task_categories:
- text-generation
- text-to-speech
language:
- en
tags:
- manim
- manim-voiceover
- educational-video
- synthetic-dataset
- aos
size_categories:
- n<1K
---

# {repo_id.split('/')[-1]}

This dataset contains **{sample_count} executable `manim-voiceover` scripts** converted from standard Manim Community Edition (CE) trajectories using Gemini 2.5 Flash Batch API.

## Dataset Summary

- **Total Samples:** {sample_count}
- **Format:** JSON Lines (`jsonl`)
- **Key Fields:**
  - `id`: Sample identifier
  - `narrated_manim_code`: Executable Python scene code inheriting from `VoiceoverScene` with `self.voiceover(...)` blocks and phonetic mathematical narration.
  - `status`: Conversion status (`success` / `failed`)

## Conversion Pipeline Details

1. **System Contract:** Enforces `VoiceoverScene` inheritance, initial `self.set_speech_service(GTTSService())` initialization, and phonetic expression of LaTeX symbols in spoken text.
2. **Timing Synchronization:** All visual animations inside `with self.voiceover(...) as tracker:` use `run_time=tracker.duration`.
3. **Engine:** Converted via asynchronous Google Gemini 2.5 Flash Batch API.

## Usage

```python
from datasets import load_dataset

dataset = load_dataset("{repo_id}")
print(dataset["train"][0]["narrated_manim_code"])
```

## AOS Platform Integration

Created for the **AOS (Agentic Orchestration System)** project fine-tuning pipelines.
"""


def _resolve_valid_token(token: Optional[str] = None) -> str:
    """Resolve a verified valid Hugging Face token from explicit arg, env, or CLI login."""
    candidates = []
    if token and token.strip():
        candidates.append(token.strip())
    env_tok = os.environ.get("HF_TOKEN", "").strip()
    if env_tok and env_tok not in candidates:
        candidates.append(env_tok)
    if get_token:
        try:
            disk_tok = get_token()
            if disk_tok and disk_tok not in candidates:
                candidates.append(disk_tok)
        except Exception:
            pass

    api = HfApi()
    for cand in candidates:
        try:
            user_info = api.whoami(token=cand)
            username = user_info.get("name") or user_info.get("fullname")
            print(f"Authenticated as Hugging Face user: {username}")
            return cand
        except Exception:
            continue

    print(
        "ERROR: No valid Hugging Face token found. Run `huggingface-cli login` or set HF_TOKEN.",
        file=sys.stderr,
    )
    sys.exit(1)


def upload_narrated_dataset(
    repo_id: str,
    dataset_path: Path,
    token: Optional[str] = None,
    private: bool = False,
) -> None:
    """Create HF dataset repository and upload dataset file and README.md."""
    if HfApi is None:
        raise ImportError(
            "The 'huggingface-hub' package is required. Install with `uv add huggingface-hub`."
        )

    resolved_token = _resolve_valid_token(token)

    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    # Count sample records
    sample_count = 0
    with open(dataset_path, "r", encoding="utf-8") as f:
        sample_count = sum(1 for line in f if line.strip())

    api = HfApi(token=resolved_token)

    print(f"Creating repository on Hugging Face: https://huggingface.co/datasets/{repo_id}")
    api.create_repo(
        repo_id=repo_id,
        repo_type="dataset",
        private=private,
        exist_ok=True,
        token=resolved_token,
    )

    print(f"Uploading dataset file: {dataset_path.name} -> {repo_id}/train.jsonl")
    api.upload_file(
        path_or_fileobj=str(dataset_path),
        path_in_repo="train.jsonl",
        repo_id=repo_id,
        repo_type="dataset",
        token=resolved_token,
    )

    # Also upload as manim_narrated_400.jsonl for explicit naming
    api.upload_file(
        path_or_fileobj=str(dataset_path),
        path_in_repo="manim_narrated_400.jsonl",
        repo_id=repo_id,
        repo_type="dataset",
        token=resolved_token,
    )

    # Generate and upload dataset README.md
    card_content = generate_dataset_card(repo_id, sample_count)
    readme_path = dataset_path.parent / "README.md"
    readme_path.write_text(card_content, encoding="utf-8")

    print(f"Uploading Dataset Card -> {repo_id}/README.md")
    api.upload_file(
        path_or_fileobj=str(readme_path),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset",
        token=resolved_token,
    )

    print(f"Successfully uploaded dataset to: https://huggingface.co/datasets/{repo_id}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Upload AOS Narrated Manim dataset to Hugging Face Hub"
    )
    parser.add_argument(
        "--repo-id",
        default=DEFAULT_REPO_ID,
        help=f"HuggingFace dataset repository ID (default: {DEFAULT_REPO_ID})",
    )
    parser.add_argument(
        "--dataset-path",
        type=Path,
        default=DEFAULT_DATASET_FILE,
        help=f"Path to manim_narrated_400.jsonl (default: {DEFAULT_DATASET_FILE})",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Make the HuggingFace repository private",
    )
    return parser


def main() -> int:
    init_environment()
    args = build_arg_parser().parse_args()
    try:
        upload_narrated_dataset(
            repo_id=args.repo_id,
            dataset_path=args.dataset_path.resolve(),
            private=args.private,
        )
        return 0
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
