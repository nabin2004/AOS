#!/usr/bin/env python3
"""DPO on AOS trajectory preference pairs, initialized from SFT LoRA.

Usage (from apps/dpo):

    uv run python run.py \\
      --sft-lora ../qwenCoder/qwen2.5-coder-7b-manim-ft \\
      --data-path ../agents/export_traces/coder_sft/preference/train.jsonl
"""

from __future__ import annotations

from dataclasses import replace

from trl import DPOTrainer

from config import TrainingConfig, build_arg_parser
from data import load_preference_dataset
from model import load_policy_model, load_tokenizer


def main() -> int:
    args = build_arg_parser().parse_args()
    config = TrainingConfig.from_cli(args)

    if args.smoke:
        config = replace(config, epochs=1, report_to="none")

    if not config.data_path.is_file():
        print(f"ERROR: preference file not found: {config.data_path}")
        print("Run: uv run python apps/agents/build_preference_pairs.py")
        return 1

    config.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Base: {config.model_id}")
    print(f"SFT:  {config.sft_lora_path}")
    print(f"Data: {config.data_path}")

    tokenizer = load_tokenizer(config.model_id)
    model = load_policy_model(config)
    limit = 8 if args.smoke else None
    train_ds = load_preference_dataset(config.data_path, tokenizer, limit=limit)
    eval_ds = None
    if config.eval_path is not None and config.eval_path.is_file():
        eval_ds = load_preference_dataset(
            config.eval_path, tokenizer, limit=4 if args.smoke else None
        )

    trainer = DPOTrainer(
        model=model,
        args=config.dpo_config(),
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        processing_class=tokenizer,
        peft_config=config.lora_config(),
    )
    trainer.train()
    trainer.save_model(str(config.output_dir))
    tokenizer.save_pretrained(str(config.output_dir))
    print(f"DPO adapter saved to {config.output_dir}")

    if config.push_to_hub:
        import sys
        from pathlib import Path

        qwen = Path(__file__).resolve().parent.parent / "qwenCoder"
        sys.path.insert(0, str(qwen))
        from hub_upload import push_model_folder, require_token

        token = require_token()
        push_model_folder(
            config.output_dir,
            config.hub_model_id,
            token,
            private=config.hub_private,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
