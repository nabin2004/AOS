#!/usr/bin/env python3
"""Prepare Continued SFT and DPO preference datasets from 400 Manim narrated scripts.

Inputs:
- Narrated dataset: apps/sft/dataset_narrated/manim_narrated_400.jsonl
- Curated mix: apps/qwenCoder/curated_sft_5k_400/train.jsonl

Outputs:
1. Continued SFT dataset (chat messages format):
   apps/qwenCoder/data_narrated_sft/train.jsonl
2. DPO preference dataset (prompt / chosen / rejected):
   apps/qwenCoder/data_narrated_dpo/train.jsonl

Usage:
    uv run python prepare_narrated_datasets.py
    uv run python prepare_narrated_datasets.py --push-dpo --dpo-repo nabin2004/manim-narrated-dpo-400
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from huggingface_hub import HfApi, get_token
except ImportError:
    HfApi = None
    get_token = None

QWEN_ROOT = Path(__file__).resolve().parent
REPO_ROOT = QWEN_ROOT.parent.parent
SFT_ROOT = QWEN_ROOT.parent / "sft"

DEFAULT_NARRATED_PATH = SFT_ROOT / "dataset_narrated" / "manim_narrated_400.jsonl"
DEFAULT_CURATED_PATH = QWEN_ROOT / "curated_sft_5k_400" / "train.jsonl"
DEFAULT_SFT_OUT_DIR = QWEN_ROOT / "data_narrated_sft"
DEFAULT_DPO_OUT_DIR = QWEN_ROOT / "data_narrated_dpo"
DEFAULT_DPO_REPO = "nabin2004/manim-narrated-dpo-400"


def _format_code_block(code_str: str) -> str:
    code_str = code_str.strip()
    if code_str.startswith("```python") and code_str.endswith("```"):
        return code_str
    if code_str.startswith("```") and code_str.endswith("```"):
        return code_str
    return f"```python\n{code_str}\n```"


def prepare_datasets(
    narrated_path: Path,
    curated_path: Path,
    sft_out_dir: Path,
    dpo_out_dir: Path,
) -> tuple[Path, Path, int]:
    """Align narrated codes with original prompts and output SFT & DPO datasets."""
    if not narrated_path.is_file():
        raise FileNotFoundError(f"Narrated file not found: {narrated_path}")
    if not curated_path.is_file():
        raise FileNotFoundError(f"Curated file not found: {curated_path}")

    # 1. Load narrated codes
    narrated_map: Dict[str, str] = {}
    with open(narrated_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                if item.get("status") == "success" and item.get("narrated_manim_code"):
                    narrated_map[item["id"]] = item["narrated_manim_code"].strip()
            except json.JSONDecodeError:
                continue

    print(f"Loaded {len(narrated_map)} verified narrated scripts from: {narrated_path}")

    # 2. Align with original prompts and un-narrated code
    sft_records: List[Dict[str, Any]] = []
    dpo_records: List[Dict[str, Any]] = []

    with open(curated_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if not line.strip():
                continue
            sample_id = f"sample_{idx}"
            if sample_id not in narrated_map:
                continue

            try:
                curated_data = json.loads(line)
                messages = curated_data.get("messages", [])
                if len(messages) < 2:
                    continue

                user_prompt = ""
                orig_code = ""
                system_prompt = ""
                for msg in messages:
                    role = msg.get("role")
                    content = msg.get("content", "").strip()
                    if role == "user":
                        user_prompt = content
                    elif role == "assistant":
                        orig_code = content
                    elif role == "system":
                        system_prompt = content

                narrated_code = narrated_map[sample_id]

                if not user_prompt or not narrated_code:
                    continue

                chosen_code = _format_code_block(narrated_code)
                rejected_code = _format_code_block(orig_code)

                # Continued SFT record (chat messages format)
                sft_chat_messages = []
                if system_prompt:
                    sft_chat_messages.append({"role": "system", "content": system_prompt})
                sft_chat_messages.append({"role": "user", "content": user_prompt})
                sft_chat_messages.append({"role": "assistant", "content": chosen_code})

                sft_records.append(
                    {
                        "messages": sft_chat_messages,
                        "metadata": {
                            "id": sample_id,
                            "source": "manim_voiceover_narrated_400",
                        },
                    }
                )

                # DPO preference record (prompt, chosen, rejected)
                dpo_records.append(
                    {
                        "prompt": user_prompt,
                        "chosen": chosen_code,
                        "rejected": rejected_code,
                        "metadata": {
                            "id": sample_id,
                            "source": "manim_voiceover_dpo_400",
                        },
                    }
                )

            except json.JSONDecodeError:
                continue

    aligned_count = len(sft_records)
    print(f"Successfully aligned {aligned_count} samples for SFT and DPO.")

    # 3. Write Continued SFT dataset
    sft_out_dir.mkdir(parents=True, exist_ok=True)
    sft_file = sft_out_dir / "train.jsonl"
    with open(sft_file, "w", encoding="utf-8") as out:
        for rec in sft_records:
            out.write(json.dumps(rec) + "\n")
    print(f"Saved Continued SFT dataset ({aligned_count} rows): {sft_file}")

    # 4. Write DPO preference dataset
    dpo_out_dir.mkdir(parents=True, exist_ok=True)
    dpo_file = dpo_out_dir / "train.jsonl"
    with open(dpo_file, "w", encoding="utf-8") as out:
        for rec in dpo_records:
            out.write(json.dumps(rec) + "\n")
    print(f"Saved DPO preference dataset ({aligned_count} rows): {dpo_file}")

    return sft_file, dpo_file, aligned_count


def upload_dpo_dataset_to_hub(
    dpo_file: Path,
    repo_id: str = DEFAULT_DPO_REPO,
    token: Optional[str] = None,
) -> None:
    """Upload DPO preference dataset to Hugging Face Hub."""
    if HfApi is None:
        raise ImportError("huggingface-hub is required for hub upload.")

    resolved_token = token or os.environ.get("HF_TOKEN") or (get_token() if get_token else None)
    api = HfApi(token=resolved_token)

    print(f"Creating DPO dataset repository on Hugging Face: {repo_id}")
    api.create_repo(repo_id=repo_id, repo_type="dataset", exist_ok=True, token=resolved_token)

    print(f"Uploading {dpo_file} -> {repo_id}/train.jsonl")
    api.upload_file(
        path_or_fileobj=str(dpo_file),
        path_in_repo="train.jsonl",
        repo_id=repo_id,
        repo_type="dataset",
        token=resolved_token,
    )

    readme_content = f"""---
license: mit
task_categories:
- text-generation
language:
- en
tags:
- dpo
- preference
- manim
- manim-voiceover
- aos
size_categories:
- n<1K
---

# {repo_id.split('/')[-1]}

Direct Preference Optimization (DPO) dataset pairing **400 narrated `VoiceoverScene` scripts** (`chosen`) against **un-narrated silent `Scene` scripts** (`rejected`).

- **Chosen**: Executable `VoiceoverScene` with `self.set_speech_service(GTTSService())`, animation duration tracking, and phonetic math intuition.
- **Rejected**: Silent, un-narrated standard Manim `Scene` code.
"""
    readme_path = dpo_file.parent / "README.md"
    readme_path.write_text(readme_content, encoding="utf-8")

    api.upload_file(
        path_or_fileobj=str(readme_path),
        path_in_repo="README.md",
        repo_id=repo_id,
        repo_type="dataset",
        token=resolved_token,
    )
    print(f"Successfully published DPO dataset: https://huggingface.co/datasets/{repo_id}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Continued SFT and DPO datasets from narrated Manim scripts")
    parser.add_argument("--narrated-path", type=Path, default=DEFAULT_NARRATED_PATH)
    parser.add_argument("--curated-path", type=Path, default=DEFAULT_CURATED_PATH)
    parser.add_argument("--sft-out-dir", type=Path, default=DEFAULT_SFT_OUT_DIR)
    parser.add_argument("--dpo-out-dir", type=Path, default=DEFAULT_DPO_OUT_DIR)
    parser.add_argument("--push-dpo", action="store_true", help="Push DPO dataset to Hugging Face")
    parser.add_argument("--dpo-repo", default=DEFAULT_DPO_REPO, help="DPO dataset Hugging Face repository ID")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    sft_file, dpo_file, count = prepare_datasets(
        narrated_path=args.narrated_path.resolve(),
        curated_path=args.curated_path.resolve(),
        sft_out_dir=args.sft_out_dir.resolve(),
        dpo_out_dir=args.dpo_out_dir.resolve(),
    )
    if args.push_dpo:
        upload_dpo_dataset_to_hub(dpo_file, repo_id=args.dpo_repo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
