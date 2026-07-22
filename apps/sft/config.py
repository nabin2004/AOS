from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, replace
from pathlib import Path

from peft import LoraConfig
from trl import SFTConfig

SFT_ROOT = Path(__file__).resolve().parent


@dataclass
class TrainingConfig:
    model_id: str = "google/gemma-4-E2B-it"
    dataset_repo: str = "nabin2004/AOS-Trajectories"
    dataset_file: str = "trajectories.jsonl"
    data_path: Path | None = None
    output_dir: Path = SFT_ROOT / "gemma4-manim-ft"
    use_4bit: bool = True
    seq_len: int = 8192
    epochs: int = 2
    batch_size: int = 2
    grad_accum: int = 4
    learning_rate: float = 5e-6
    num_proc: int = 8
    report_to: str = "wandb"
    run_name: str = "gemma4-manim-sft"
    wandb_project: str = "aos-sft"
    attn_implementation: str = "sdpa"

    def resolve_paths(self) -> TrainingConfig:
        data_path = self.data_path
        if data_path is not None:
            data_path = _resolve_path(data_path)
        return replace(
            self,
            data_path=data_path,
            output_dir=_resolve_path(self.output_dir),
        )

    def lora_config(self) -> LoraConfig:
        return LoraConfig(
            r=64,
            lora_alpha=128,
            lora_dropout=0.05,
            target_modules=[
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
            bias="none",
            task_type="CAUSAL_LM",
            modules_to_save=["embed_tokens", "lm_head"],
        )

    def sft_config(self) -> SFTConfig:
        logging_dir = os.environ.get("AIP_TENSORBOARD_LOG_DIR") or None
        return SFTConfig(
            output_dir=str(self.output_dir),
            logging_dir=logging_dir,
            num_train_epochs=self.epochs,
            per_device_train_batch_size=self.batch_size,
            gradient_accumulation_steps=self.grad_accum,
            gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
            use_cache=False,
            learning_rate=self.learning_rate,
            lr_scheduler_type="cosine",
            warmup_ratio=0.03,
            optim="adamw_torch_fused",
            bf16=True,
            logging_steps=10,
            save_strategy="epoch",
            packing=True,
            max_seq_length=self.seq_len,
            assistant_only_loss=True,
            dataset_kwargs={"add_special_tokens": False},
            report_to=self.report_to,
            run_name=self.run_name,
        )

    @classmethod
    def from_cli(cls, args: argparse.Namespace) -> TrainingConfig:
        config = cls().resolve_paths()
        if args.data_path is not None:
            config = replace(config, data_path=_resolve_path(Path(args.data_path)))
        if args.dataset_repo is not None:
            config = replace(config, dataset_repo=args.dataset_repo)
        if args.dataset_file is not None:
            config = replace(config, dataset_file=args.dataset_file)
        if args.output_dir is not None:
            config = replace(config, output_dir=_resolve_path(Path(args.output_dir)))
        if args.model_id is not None:
            config = replace(config, model_id=args.model_id)
        if args.epochs is not None:
            config = replace(config, epochs=args.epochs)
        if args.batch_size is not None:
            config = replace(config, batch_size=args.batch_size)
        if args.learning_rate is not None:
            config = replace(config, learning_rate=args.learning_rate)
        if args.no_4bit:
            config = replace(config, use_4bit=False)
        if args.report_to is not None:
            config = replace(config, report_to=args.report_to)
        return apply_vertex_env(config)


def apply_vertex_env(config: TrainingConfig) -> TrainingConfig:
    model_dir = os.environ.get("AIP_MODEL_DIR", "").strip()
    if model_dir:
        config = replace(config, output_dir=Path(model_dir))

    tb_dir = os.environ.get("AIP_TENSORBOARD_LOG_DIR", "").strip()
    if tb_dir and config.report_to != "none" and config.report_to == "wandb":
        config = replace(config, report_to="tensorboard")
    return config


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (Path.cwd() / path).resolve()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fine-tune Gemma 4 on agent trajectories"
    )
    parser.add_argument(
        "--data-path",
        default=None,
        help="Local trajectory JSONL override (default: Hugging Face dataset)",
    )
    parser.add_argument(
        "--dataset-repo",
        default=None,
        help='HF dataset id (default: "nabin2004/AOS-Trajectories")',
    )
    parser.add_argument(
        "--dataset-file",
        default=None,
        help='File within HF dataset repo (default: "trajectories.jsonl")',
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for adapter weights and tokenizer",
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help='Hugging Face model id (default: "google/gemma-4-E2B-it")',
    )
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument(
        "--no-4bit",
        action="store_true",
        help="Disable 4-bit quantization (requires ~80GB+ VRAM for full BF16)",
    )
    parser.add_argument(
        "--report-to",
        default=None,
        help='Logging backend (default: "wandb"; use "none" to disable)',
    )
    return parser
