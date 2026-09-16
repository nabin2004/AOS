#!/usr/bin/env python3
"""Standalone dataset uploader for qwen-Manimator-1-sft-data.

Uploads apps/new_data/train.jsonl to:
  https://huggingface.co/datasets/nabin2004/qwen-Manimator-1-sft-data

Usage:
    uv run python upload_manimator_dataset.py
    uv run python upload_manimator_dataset.py --repo-id nabin2004/qwen-Manimator-1-sft-data
    uv run python upload_manimator_dataset.py --dry-run  # validate only, no upload
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

QWEN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = QWEN_ROOT.parent.parent
DEFAULT_DATASET = REPO_ROOT / "apps" / "new_data" / "train.jsonl"
DEFAULT_REPO_ID = "nabin2004/qwen-Manimator-1-sft-data"


def validate_jsonl(path: Path) -> int:
    """Validate each line is parseable JSON with the expected messages schema."""
    errors: list[tuple[int, str]] = []
    count = 0
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            count += 1
            try:
                row = json.loads(line)
                msgs = row.get("messages", [])
                if not msgs or msgs[-1].get("role") != "assistant":
                    errors.append((i, "last message must be 'assistant'"))
            except json.JSONDecodeError as exc:
                errors.append((i, f"JSON parse error: {exc}"))
    if errors:
        for lineno, msg in errors[:20]:
            print(f"  line {lineno}: {msg}", file=sys.stderr)
        raise ValueError(f"Found {len(errors)} validation errors in {path}")
    print(f"✔ Validated {count} examples in {path}")
    return count


def build_readme(repo_id: str, n_examples: int) -> str:
    return f"""---
license: apache-2.0
task_categories:
  - text-generation
language:
  - en
tags:
  - manim
  - manim-voiceover
  - manimce
  - code-generation
  - sft
  - aos
  - qwen3
pretty_name: qwen-Manimator-1 SFT Dataset
size_categories:
  - n<1K
---

# qwen-Manimator-1 SFT Dataset

**{n_examples} chat-format JSONL examples** used to fine-tune
[`nabin2004/qwen-Manimator-1-sft`](https://huggingface.co/nabin2004/qwen-Manimator-1-sft)
— a Qwen/Qwen3-8B LoRA SFT adapter for generating pedagogically rich
**ManimCE + Manim Voiceover** animated scenes.

## Dataset Format

Each row is a `messages`-format JSONL object:

```json
{{
  "messages": [
    {{"role": "system",    "content": "You are an expert..."}},
    {{"role": "user",      "content": "Create a visualization of..."}},
    {{"role": "assistant", "content": "<Plan>...\\n```python\\n...\\n```"}}
  ]
}}
```

### Assistant Output Contract

Every assistant message must contain:
- A `<Plan>` block describing the animation intent.
- One fenced Python code block.
- `VoiceoverScene` inheritance.
- `AOSSpeechService` initialization via `set_speech_service(...)`.
- `<bookmark mark='NAME'/>` tags in voiceover text.
- `self.wait_until_bookmark("NAME")` calls matching every bookmark.

## Models

| Artifact | Repository |
|---|---|
| LoRA Adapter | [`nabin2004/qwen-Manimator-1-sft`](https://huggingface.co/nabin2004/qwen-Manimator-1-sft) |
| Merged Model | [`nabin2004/qwen-Manimator-1-merged`](https://huggingface.co/nabin2004/qwen-Manimator-1-merged) |
| GGUF Q4+Q8   | [`nabin2004/qwen-Manimator-1-gguf`](https://huggingface.co/nabin2004/qwen-Manimator-1-gguf) |

## Training Config

| Parameter | Value |
|---|---|
| Base Model | `Qwen/Qwen3-8B` |
| Epochs | 3 |
| Batch Size | 1 (grad_accum 8, effective 16/GPU) |
| Max Length | 4500 |
| Learning Rate | 1e-4 |
| LoRA | r=16, alpha=32 |
| Optimizer | paged_adamw_8bit |
| Hardware | Kaggle T4×2 (2×16 GB) |
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-path",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"Path to train.jsonl (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--repo-id",
        default=DEFAULT_REPO_ID,
        help=f"HF dataset repo ID (default: {DEFAULT_REPO_ID})",
    )
    parser.add_argument(
        "--private", action="store_true", help="Upload as a private repository"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate dataset only; do not upload",
    )
    args = parser.parse_args()

    dataset_path = args.dataset_path.expanduser().resolve()
    if not dataset_path.is_file():
        print(f"ERROR: Dataset not found at {dataset_path}", file=sys.stderr)
        return 1

    print(f"\n==> Validating {dataset_path}...")
    try:
        n_examples = validate_jsonl(dataset_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print("Dry run complete. Dataset is valid.")
        return 0

    import io
    import os

    try:
        from huggingface_hub import HfApi, get_token  # type: ignore
    except ImportError:
        print("ERROR: huggingface-hub is required. Run: pip install huggingface-hub", file=sys.stderr)
        return 1

    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        try:
            token = get_token() or ""
        except Exception:
            token = ""
    if not token:
        print(
            "ERROR: HF_TOKEN not found. Set the HF_TOKEN environment variable.",
            file=sys.stderr,
        )
        return 1

    api = HfApi(token=token)
    print(f"\n==> Creating/updating dataset repo: https://huggingface.co/datasets/{args.repo_id}")
    api.create_repo(
        repo_id=args.repo_id,
        repo_type="dataset",
        exist_ok=True,
        private=args.private,
        token=token,
    )

    print(f"==> Uploading {dataset_path.name} ({dataset_path.stat().st_size / 1e6:.1f} MB)...")
    api.upload_file(
        path_or_fileobj=str(dataset_path),
        path_in_repo="train.jsonl",
        repo_id=args.repo_id,
        repo_type="dataset",
        token=token,
    )

    readme = build_readme(args.repo_id, n_examples)
    api.upload_file(
        path_or_fileobj=io.BytesIO(readme.encode()),
        path_in_repo="README.md",
        repo_id=args.repo_id,
        repo_type="dataset",
        token=token,
    )

    print(f"\n✔ Dataset successfully uploaded!")
    print(f"  URL: https://huggingface.co/datasets/{args.repo_id}")
    print(f"  Rows: {n_examples}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
