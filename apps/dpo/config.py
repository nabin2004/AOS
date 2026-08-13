"""DPO training config for AOS preference pairs (Qwen or Gemma adapters)."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from pathlib import Path

from peft import LoraConfig
from trl import DPOConfig

DPO_ROOT = Path(__file__).resolve().parent
QWEN_ROOT = DPO_ROOT.parent / "qwenCoder"

import sys

if str(QWEN_ROOT) not in sys.path:
    sys.path.insert(0, str(QWEN_ROOT))

from identity import (  # noqa: E402
    BASE_MODEL_ID,
    DPO_OUTPUT_DIR_NAME,
    HUB_DPO_REPO,
    WANDB_DPO_RUN_NAME,
    WANDB_RUN_GROUP,
    WANDB_TAGS,
)

LORA_TARGETS = (
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
)


@dataclass
class TrainingConfig:
    model_id: str = BASE_MODEL_ID
    sft_lora_path: Path | None = None
    data_path: Path = (
        DPO_ROOT.parent / "agents" / "export_traces" / "coder_sft" / "preference" / "train.jsonl"
    )
    eval_path: Path | None = (
        DPO_ROOT.parent / "agents" / "export_traces" / "coder_sft" / "preference" / "val.jsonl"
    )
    output_dir: Path = DPO_ROOT / DPO_OUTPUT_DIR_NAME
    use_4bit: bool = True
    seq_len: int = 2048
    epochs: int = 1
    batch_size: int = 1
    grad_accum: int = 8
    learning_rate: float = 5e-7
    beta: float = 0.1
    report_to: str = "none"
    run_name: str = WANDB_DPO_RUN_NAME
    wandb_project: str = "aos-dpo"
    wandb_group: str = WANDB_RUN_GROUP
    wandb_tags: tuple[str, ...] = WANDB_TAGS
    push_to_hub: bool = False
    hub_model_id: str = HUB_DPO_REPO
    hub_private: bool = False

    def resolve_paths(self) -> TrainingConfig:
        eval_path = self.eval_path
        if eval_path is not None:
            eval_path = eval_path.expanduser().resolve()
        sft = self.sft_lora_path
        if sft is not None:
            sft = sft.expanduser().resolve()
        return replace(
            self,
            data_path=self.data_path.expanduser().resolve(),
            eval_path=eval_path,
            sft_lora_path=sft,
            output_dir=self.output_dir.expanduser().resolve(),
        )

    def lora_config(self) -> LoraConfig:
        return LoraConfig(
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            target_modules=list(LORA_TARGETS),
            bias="none",
            task_type="CAUSAL_LM",
        )

    def dpo_config(self) -> DPOConfig:
        return DPOConfig(
            output_dir=str(self.output_dir),
            num_train_epochs=self.epochs,
            per_device_train_batch_size=self.batch_size,
            gradient_accumulation_steps=self.grad_accum,
            learning_rate=self.learning_rate,
            beta=self.beta,
            max_length=self.seq_len,
            max_prompt_length=self.seq_len // 2,
            bf16=True,
            logging_steps=10,
            save_strategy="epoch",
            report_to=self.report_to,
            run_name=self.run_name,
            remove_unused_columns=False,
        )

    @classmethod
    def from_cli(cls, args: argparse.Namespace) -> TrainingConfig:
        config = cls().resolve_paths()
        if args.model_id:
            config = replace(config, model_id=args.model_id)
        if args.sft_lora:
            config = replace(config, sft_lora_path=Path(args.sft_lora))
        if args.data_path:
            config = replace(config, data_path=Path(args.data_path))
        if args.eval_path:
            config = replace(config, eval_path=Path(args.eval_path))
        if args.output_dir:
            config = replace(config, output_dir=Path(args.output_dir))
        if args.epochs is not None:
            config = replace(config, epochs=args.epochs)
        if args.beta is not None:
            config = replace(config, beta=args.beta)
        if args.no_4bit:
            config = replace(config, use_4bit=False)
        if args.report_to:
            config = replace(config, report_to=args.report_to)
        if args.push_to_hub:
            config = replace(config, push_to_hub=True)
        if args.hub_model_id:
            config = replace(config, hub_model_id=args.hub_model_id)
        return config.resolve_paths()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AOS DPO on trajectory preference pairs")
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--sft-lora", type=Path, default=None)
    parser.add_argument("--data-path", type=Path, default=None)
    parser.add_argument("--eval-path", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--beta", type=float, default=None)
    parser.add_argument("--no-4bit", action="store_true")
    parser.add_argument("--report-to", default=None)
    parser.add_argument("--push-to-hub", action="store_true")
    parser.add_argument("--hub-model-id", default=None)
    parser.add_argument("--smoke", action="store_true")
    return parser
