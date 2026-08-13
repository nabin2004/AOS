#!/usr/bin/env python3
"""GRPO Phase 2: ManiBench training on stacked SFT + GRPO LoRA (Gemma 4).

Usage (from apps/grpo):

    uv run python run.py --smoke
    uv run python run.py --sft-lora ../sft/gemma4-31b-manim-ft
    uv run python run.py --dataset-path ./ManiBench_Pilot_Dataset.json
"""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

from config import TrainingConfig, build_arg_parser
from manibench import build_dataset
from model import check_cuda_or_exit, load_model
from trainer import (
    build_trainer,
    make_training_args,
    resolve_max_completion_length,
    train_and_save,
    truncate_dataset_prompts,
)

TRAINING_ROOT = Path(__file__).resolve().parent.parent / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from wandb_env import configure_wandb, resolve_report_to  # noqa: E402
from model_identity import BASE_MODEL_ID, HUB_SFT_REPO  # noqa: E402


def main() -> int:
    config = TrainingConfig.from_cli(build_arg_parser().parse_args())

    if config.report_to == "wandb":
        effective = configure_wandb(
            project=config.wandb_project,
            run_name=config.run_name,
            job_type="grpo",
            project_env_key="WANDB_PROJECT_GRPO",
            group=config.wandb_group,
            tags=[*config.wandb_tags, "grpo"],
            config={
                "base_model": config.base_model or BASE_MODEL_ID,
                "sft_lora_path": str(config.sft_lora_path),
                "hub_sft_repo": HUB_SFT_REPO,
                "output_dir": str(config.output_dir),
                "load_in_4bit": config.load_in_4bit,
            },
        )
        config = replace(config, report_to=effective)
    else:
        config = replace(config, report_to=resolve_report_to(config.report_to))

    config.apply_env()
    check_cuda_or_exit()

    if config.base_family != "qwen":
        import unsloth  # noqa: F401 — must precede trl for Gemma/Unsloth path

    model, tokenizer = load_model(config)
    dataset = truncate_dataset_prompts(
        build_dataset(config),
        tokenizer,
        config.max_prompt_length,
    )

    completion_cap = 256 if config.smoke else config.max_completion_length
    max_completion_length = resolve_max_completion_length(
        dataset,
        tokenizer,
        config,
        cap=completion_cap,
    )
    os.environ["MANIBENCH_MAX_COMPLETION_LENGTH"] = str(max_completion_length)

    print(
        f"Settings: load_in_4bit={config.load_in_4bit}, grpo_only={config.grpo_only}, "
        f"repeat_factor={config.repeat_factor}, rows={len(dataset)}, "
        f"max_prompt_length={config.max_prompt_length}, "
        f"max_completion_length={max_completion_length}, "
        f"num_generations={config.num_generations}, "
        f"length_penalty={config.length_penalty}, "
        f"report_to={config.report_to}, "
        f"render={os.environ.get('MANIBENCH_GRPO_RENDER', '0')}",
        flush=True,
    )

    training_args = make_training_args(
        config, max_completion_length=max_completion_length
    )
    trainer = build_trainer(model, tokenizer, dataset, config, training_args)
    train_and_save(trainer, model, tokenizer, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
