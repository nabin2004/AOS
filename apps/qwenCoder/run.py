#!/usr/bin/env python3
"""Fine-tune Qwen2.5-Coder-7B on AOS Code Agent tool-trace trajectories.

Usage (from apps/qwenCoder):

    uv run python run.py --data-path ../agents/export_traces/coder_sft/tool_trace.train.jsonl
    uv run python run.py --dataset-repo nabin2004/AOS-Qwen-Trajectories --push-to-hub
"""

from __future__ import annotations

from dataclasses import replace

from config import TrainingConfig, build_arg_parser
from data import load_training_dataset
from model import load_model, load_tokenizer
from trainer import build_trainer, train_and_save


def main() -> int:
    args = build_arg_parser().parse_args()
    config = TrainingConfig.from_cli(args)

    if args.smoke:
        config = replace(
            config,
            epochs=1,
            seq_len=1024,
            report_to="none",
        )

    config.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Base model: {config.model_id}")
    print(f"Output:     {config.output_dir}")

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
