#!/usr/bin/env python3
"""Fine-tune Qwen2.5-Coder-7B on staged Manim SFT corpora.

Usage (from apps/qwenCoder):

    uv run python run.py --dataset-repo nabin2004/manim-sft --stage manim
    uv run python run.py --dataset-repo nabin2004/educlaw-manim-sft \\
      --max-samples 20000 --init-adapter ./qwen2.5-coder-7b-manim-ft --stage educlaw
    uv run python run.py --dataset-repo nabin2004/AOS-Trajectories \\
      --dataset-file tool_trace/train.jsonl --init-adapter ./qwen2.5-coder-7b-manim-ft \\
      --stage traces
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

from config import TrainingConfig, build_arg_parser, effective_bf16
from data import load_training_dataset, native_sft_chat_repo
from model import load_model, load_tokenizer
from trainer import build_trainer, train_and_save

TRAINING_ROOT = Path(__file__).resolve().parent.parent / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from wandb_env import configure_wandb, resolve_report_to  # noqa: E402


def _apply_wandb(config: TrainingConfig) -> TrainingConfig:
    if config.report_to == "wandb":
        effective = configure_wandb(
            project=config.wandb_project,
            run_name=config.run_name,
            job_type="sft",
            project_env_key="WANDB_PROJECT_QWEN_SFT",
            group=config.wandb_group,
            tags=[*config.wandb_tags],
            config={
                "model_id": config.model_id,
                "dataset_repo": config.dataset_repo,
                "dataset_file": config.dataset_file,
                "stage": config.stage,
                "max_samples": config.max_samples,
                "init_adapter": str(config.init_adapter) if config.init_adapter else None,
                "epochs": config.epochs,
                "seq_len": config.seq_len,
                "learning_rate": config.learning_rate,
            },
        )
        return replace(config, report_to=effective)
    return replace(config, report_to=resolve_report_to(config.report_to))


def main() -> int:
    args = build_arg_parser().parse_args()
    config = TrainingConfig.from_cli(args)

    if args.smoke:
        config = replace(
            config,
            epochs=1,
            seq_len=1024,
            report_to="none",
            max_samples=8 if config.max_samples is None else min(config.max_samples, 8),
        )

    config = _apply_wandb(config)

    config.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Base model: {config.model_id}")
    print(f"Output:     {config.output_dir}")
    if native_sft_chat_repo(config.dataset_repo):
        print(f"Dataset:    {config.dataset_repo}  [SFT chat messages]")
    elif config.data_path is not None:
        print(f"Dataset:    {config.data_path}")
    else:
        print(f"Dataset:    {config.dataset_repo} ({config.dataset_file})")
    if config.stage:
        print(f"Stage:      {config.stage}")
    if config.init_adapter:
        print(f"Init LoRA:  {config.init_adapter}")
    print(f"report_to:  {config.report_to}")
    print(f"use_bf16:   {config.use_bf16} (effective {effective_bf16(config.use_bf16)})")
    print(
        f"QLoRA:      r={config.lora_r} alpha={config.lora_alpha} "
        f"4bit={config.use_4bit} packing={config.packing} "
        f"max_samples={config.max_samples}"
    )

    tokenizer = load_tokenizer(config.model_id)
    model = load_model(config)
    dataset = load_training_dataset(config)
    if args.smoke and len(dataset) > 8:
        dataset = dataset.select(range(8))

    trainer = build_trainer(model, tokenizer, dataset, config)
    train_and_save(trainer, tokenizer, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
