#!/usr/bin/env python3
"""Upload AOS SFT LoRA adapter to Hugging Face Hub.

Requires HF_TOKEN in the environment (write access). Never commit tokens.

Usage (from apps/sft):

    export HF_TOKEN=hf_...
    uv run python upload_adapter.py
    uv run python upload_adapter.py --adapter-dir ./gemma4-31b-manim-ft
    uv run python upload_adapter.py --adapter-dir /content/gemma4-31b-manim-ft --colab
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config import (
    TrainingConfig,
    apply_colab_preset,
    default_colab_output_dir,
    is_colab_runtime,
)
from hub_upload import push_model_folder, require_token

SFT_ROOT = Path(__file__).resolve().parent
TRAINING_ROOT = SFT_ROOT.parent / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from model_identity import HUB_SFT_REPO, SFT_OUTPUT_DIR_NAME  # noqa: E402

DEFAULT_REPO_ID = HUB_SFT_REPO
MODEL_CARD = SFT_ROOT / "model_card.md"

UPLOAD_IGNORE_PATTERNS = [
    "checkpoint-*",
    "runs/*",
    "trainer_state.json",
    "training_args.bin",
    "README.md",
]


def upload_adapter(
    adapter_dir: Path,
    repo_id: str,
    token: str,
    *,
    private: bool = False,
    revision: str | None = None,
) -> None:
    adapter_dir = adapter_dir.resolve()
    adapter_config = adapter_dir / "adapter_config.json"
    if not adapter_config.is_file():
        print(
            f"ERROR: No adapter_config.json in {adapter_dir}. "
            "Point --adapter-dir at the directory saved by run.py.",
            file=sys.stderr,
        )
        sys.exit(1)

    push_model_folder(
        adapter_dir,
        repo_id,
        token,
        readme=MODEL_CARD,
        private=private,
        revision=revision,
        ignore_patterns=UPLOAD_IGNORE_PATTERNS,
    )


def default_adapter_dir(args: argparse.Namespace) -> Path:
    if args.adapter_dir is not None:
        return args.adapter_dir
    if args.colab or is_colab_runtime():
        return default_colab_output_dir()
    return TrainingConfig().output_dir


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Upload AOS SFT LoRA adapter to Hugging Face Hub"
    )
    parser.add_argument(
        "--adapter-dir",
        type=Path,
        default=None,
        help=f"Directory saved by run.py (default: {SFT_OUTPUT_DIR_NAME} or Colab path)",
    )
    parser.add_argument(
        "--repo-id",
        default=DEFAULT_REPO_ID,
        help=f"HF model repo id (default: {DEFAULT_REPO_ID})",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="Create/upload as a private model repo",
    )
    parser.add_argument(
        "--revision",
        default=None,
        help="Optional branch or tag name for the upload",
    )
    parser.add_argument(
        "--colab",
        action="store_true",
        help="Resolve default adapter dir from Colab output path",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    if args.colab or is_colab_runtime():
        apply_colab_preset(TrainingConfig())

    adapter_dir = default_adapter_dir(args)
    if not adapter_dir.is_dir():
        print(f"ERROR: Adapter directory not found: {adapter_dir}", file=sys.stderr)
        return 1

    token = require_token()
    upload_adapter(
        adapter_dir=adapter_dir,
        repo_id=args.repo_id,
        token=token,
        private=args.private,
        revision=args.revision,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
