#!/usr/bin/env python3
"""Fine-tune Gemma 4 on Code Agent trajectories.

Usage (from apps/sft):

    uv run python run.py
    uv run python run.py --data-path ../agents/training_data/trajectories.jsonl
    uv run python run.py --dataset-repo nabin2004/AOS-Trajectories
    uv run python run.py --no-4bit --report-to none
    uv run python run.py --kaggle --report-to none
"""

from __future__ import annotations

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


def main() -> int:
    parser = build_arg_parser()
    config = TrainingConfig.from_cli(parser.parse_args())

    if config.report_to == "wandb":
        effective = configure_wandb(
            project=config.wandb_project,
            run_name=config.run_name,
            job_type="sft",
            project_env_key="WANDB_PROJECT_SFT",
        )
        config = replace(config, report_to=effective)
    else:
        config = replace(config, report_to=resolve_report_to(config.report_to))

    if config.data_path is not None and not config.data_path.is_file():
        print(f"ERROR: Data file not found: {config.data_path}", file=sys.stderr)
        return 1

    config.output_dir.mkdir(parents=True, exist_ok=True)

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
