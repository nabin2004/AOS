#!/usr/bin/env python3
"""Fine-tune Gemma 4 on Manim instruction chat pairs.

Usage (from apps/sft):

    uv run python run.py
    uv run python run.py --dataset-repo nabin2004/manim-sft --dataset-file data/train.jsonl
    uv run python run.py --data-path ../agents/training_data/trajectories.jsonl
    uv run python run.py --no-4bit --report-to none
    uv run python run.py --kaggle --report-to none
    uv run python run.py --runpod --epochs 1 --report-to none
    uv run python run.py --colab --epochs 1 --report-to none
    uv run python run.py --colab --epochs 1 --report-to none --push-to-hub
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

from chat_template import prepare_training_tokenizer
from config import TrainingConfig, build_arg_parser
from data import load_training_dataset
from model import load_model, load_tokenizer
from trainer import build_trainer, train_and_save

TRAINING_ROOT = Path(__file__).resolve().parent.parent / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from wandb_env import configure_wandb, resolve_report_to  # noqa: E402
from model_identity import SFT_OUTPUT_DIR_NAME  # noqa: E402


def _is_ephemeral_colab_path(path: Path) -> bool:
    path_str = str(path)
    return path_str.startswith("/content") and not path_str.startswith("/content/drive")


def ensure_output_dir(output_dir: Path) -> int | None:
    """Validate and create output_dir; return exit code on failure."""
    path_str = str(output_dir)
    if path_str.startswith("/kaggle") and not os.environ.get("KAGGLE_KERNEL_RUN_TYPE"):
        print(
            "ERROR: /kaggle/... paths only work on Kaggle.\n"
            "On Colab use --colab (saves to Google Drive) or "
            f"--output-dir /content/drive/MyDrive/{SFT_OUTPUT_DIR_NAME}",
            file=sys.stderr,
        )
        return 1

    if _is_ephemeral_colab_path(output_dir):
        print(
            f"WARNING: Saving to {output_dir} is ephemeral. "
            "Mount Drive and use --colab or "
            f"--output-dir /content/drive/MyDrive/{SFT_OUTPUT_DIR_NAME}",
            file=sys.stderr,
        )

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(
            f"ERROR: Cannot create output directory {output_dir}: {exc}",
            file=sys.stderr,
        )
        return 1
    return None


def main() -> int:
    parser = build_arg_parser()
    config = TrainingConfig.from_cli(parser.parse_args())

    if config.report_to == "wandb":
        effective = configure_wandb(
            project=config.wandb_project,
            run_name=config.run_name,
            job_type="sft",
            project_env_key="WANDB_PROJECT_SFT",
            group=config.wandb_group,
            tags=[*config.wandb_tags, "sft"],
            config={
                "base_model": config.model_id,
                "hub_model_id": config.hub_model_id,
                "output_dir": str(config.output_dir),
                "seq_len": config.seq_len,
                "use_4bit": config.use_4bit,
                "batch_size": config.batch_size,
                "grad_accum": config.grad_accum,
            },
        )
        config = replace(config, report_to=effective)
    else:
        config = replace(config, report_to=resolve_report_to(config.report_to))

    if config.data_path is not None and not config.data_path.is_file():
        print(f"ERROR: Data file not found: {config.data_path}", file=sys.stderr)
        return 1

    if (err := ensure_output_dir(config.output_dir)) is not None:
        return err

    print(f"Output directory: {config.output_dir}")

    data_source = (
        str(config.data_path)
        if config.data_path is not None
        else f"hf://datasets/{config.dataset_repo}/{config.dataset_file}"
    )
    print(f"Loading dataset from {data_source}")

    tokenizer = load_tokenizer(config.model_id)
    config = prepare_training_tokenizer(tokenizer, config)
    dataset = load_training_dataset(config)
    model = load_model(config)
    trainer = build_trainer(model, tokenizer, dataset, config)
    train_and_save(trainer, tokenizer, config)

    if config.push_to_hub:
        from upload_adapter import require_token, upload_adapter

        upload_adapter(
            adapter_dir=config.output_dir,
            repo_id=config.hub_model_id,
            token=require_token(),
            private=config.hub_private,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
