"""Shared Hugging Face Hub upload helpers for AOS SFT artifacts."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from huggingface_hub import HfApi, get_token


def require_token() -> str:
    token = os.environ.get("HF_TOKEN", "").strip() or get_token()
    if not token:
        print(
            "ERROR: Set HF_TOKEN or run `huggingface-cli login` (write token required).",
            file=sys.stderr,
        )
        sys.exit(1)
    return token


def push_model_folder(
    folder: Path,
    repo_id: str,
    token: str,
    *,
    readme: Path | None = None,
    private: bool = False,
    revision: str | None = None,
    ignore_patterns: list[str] | None = None,
) -> str:
    folder = folder.resolve()
    if not folder.is_dir():
        raise FileNotFoundError(f"Upload directory not found: {folder}")

    patterns = list(ignore_patterns or [])
    if "README.md" not in patterns:
        patterns.append("README.md")

    api = HfApi()
    print(f"Creating model repo {repo_id} (private={private})...")
    api.create_repo(
        repo_id,
        repo_type="model",
        exist_ok=True,
        private=private,
        token=token,
    )

    print(f"Uploading {folder} -> {repo_id}")
    api.upload_folder(
        folder_path=str(folder),
        repo_id=repo_id,
        repo_type="model",
        token=token,
        revision=revision,
        ignore_patterns=patterns or None,
    )

    if readme is not None and readme.is_file():
        print(f"Uploading model card -> {repo_id}/README.md")
        api.upload_file(
            path_or_fileobj=str(readme),
            path_in_repo="README.md",
            repo_id=repo_id,
            repo_type="model",
            token=token,
            revision=revision,
        )

    url = f"https://huggingface.co/{repo_id}"
    print(f"Done: {url}")
    return url
