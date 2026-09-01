from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from peft import LoraConfig
from trl import SFTConfig

from identity import (
    BASE_MODEL_ID,
    HUB_SFT_REPO,
    SFT_OUTPUT_DIR_NAME,
    WANDB_RUN_GROUP,
    WANDB_SFT_RUN_NAME,
    WANDB_TAGS,
    stage_run_name,
    stage_tags,
)

QWEN_ROOT = Path(__file__).resolve().parent
TRAINING_ROOT = QWEN_ROOT.parent / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from wandb_env import load_training_dotenv  # noqa: E402

# Qwen2 dense MLP LoRA targets
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
    dataset_repo: str = "nabin2004/manim-sft-10k"
    dataset_file: str = "data/train.jsonl"
    dataset_split: str = "train"
    data_path: Path | None = None
    init_adapter: Path | None = None
    max_samples: int | None = None
    shuffle_seed: int = 42
    stage: str | None = None
    output_dir: Path = QWEN_ROOT / SFT_OUTPUT_DIR_NAME
    use_4bit: bool = True
    seq_len: int = 4096
    epochs: int = 1
    batch_size: int = 1
    grad_accum: int = 8
    learning_rate: float = 2e-4
    num_proc: int = 4
    report_to: str = "wandb"
    run_name: str = WANDB_SFT_RUN_NAME
    wandb_project: str = "aos-qwen-sft"
    wandb_group: str = WANDB_RUN_GROUP
    wandb_tags: tuple[str, ...] = field(default_factory=lambda: WANDB_TAGS)
    packing: bool = False
    assistant_only_loss: bool = True
    push_to_hub: bool = False
    hub_model_id: str = HUB_SFT_REPO
    hub_private: bool = False
    use_bf16: bool = True
    lora_r: int = 32
    lora_alpha: int = 64
    optim: str = "adamw_torch_fused"
    save_strategy: str = "epoch"
    save_steps: int = 200
    save_total_limit: int | None = None
    resume: str = "auto"  # auto | always | never
    resume_from: Path | None = None
    hub_checkpoint_id: str | None = None
    sync_trainer_checkpoint: bool = False
    replay_ratio: float = 0.0
    replay_dataset: str = "nabin2004/manim-sft-10k"
    eval_manibench: bool = False
    manibench_render: bool = False
    manibench_timeout: int = 20

    def resolve_paths(self) -> TrainingConfig:
        data_path = self.data_path
        if data_path is not None:
            data_path = data_path.expanduser().resolve()
        init_adapter = self.init_adapter
        if init_adapter is not None:
            init_adapter = init_adapter.expanduser().resolve()
        resume_from = self.resume_from
        if resume_from is not None:
            resume_from = resume_from.expanduser().resolve()
        return replace(
            self,
            data_path=data_path,
            init_adapter=init_adapter,
            resume_from=resume_from,
            output_dir=self.output_dir.expanduser().resolve(),
        )

    def lora_config(self) -> LoraConfig:
        return LoraConfig(
            r=self.lora_r,
            lora_alpha=self.lora_alpha,
            lora_dropout=0.05,
            target_modules=list(LORA_TARGETS),
            bias="none",
            task_type="CAUSAL_LM",
        )

    def sft_config(self) -> SFTConfig:
        use_bf16 = effective_bf16(self.use_bf16)
        return SFTConfig(
            output_dir=str(self.output_dir),
            num_train_epochs=self.epochs,
            per_device_train_batch_size=self.batch_size,
            gradient_accumulation_steps=self.grad_accum,
            gradient_checkpointing=True,
            gradient_checkpointing_kwargs={"use_reentrant": False},
            learning_rate=self.learning_rate,
            lr_scheduler_type="cosine",
            warmup_steps=10,
            optim=self.optim,
            bf16=bool(use_bf16),
            fp16=bool(not use_bf16),
            logging_steps=10,
            save_strategy=self.save_strategy,
            save_steps=self.save_steps,
            save_total_limit=self.save_total_limit,
            packing=self.packing,
            max_length=self.seq_len,
            assistant_only_loss=self.assistant_only_loss,
            dataset_kwargs={"add_special_tokens": False},
            report_to=self.report_to,
            run_name=self.run_name,
        )

    @classmethod
    def from_cli(cls, args: argparse.Namespace) -> TrainingConfig:
        load_training_dotenv()
        config = cls().resolve_paths()
        if getattr(args, "rtx3060", False):
            config = apply_rtx3060_preset(config)
        if args.kaggle or os.environ.get("KAGGLE_KERNEL_RUN_TYPE"):
            config = apply_kaggle_preset(config)
        if args.data_path is not None:
            config = replace(config, data_path=Path(args.data_path))
        if args.dataset_repo is not None:
            config = replace(config, dataset_repo=args.dataset_repo)
        if args.dataset_file is not None:
            config = replace(config, dataset_file=args.dataset_file)
        if getattr(args, "dataset_split", None) is not None:
            config = replace(config, dataset_split=args.dataset_split)
        if getattr(args, "init_adapter", None) is not None:
            config = replace(config, init_adapter=Path(args.init_adapter))
        if getattr(args, "max_samples", None) is not None:
            config = replace(config, max_samples=args.max_samples)
        if getattr(args, "shuffle_seed", None) is not None:
            config = replace(config, shuffle_seed=args.shuffle_seed)
        if getattr(args, "stage", None) is not None:
            stage = args.stage
            stage_updates: dict[str, Any] = {
                "stage": stage,
                "run_name": stage_run_name(stage),
                "wandb_tags": stage_tags(stage),
            }
            if args.dataset_repo is None:
                if stage == "manim":
                    stage_updates["dataset_repo"] = "nabin2004/manim-sft-10k"
                elif stage == "educlaw":
                    stage_updates["dataset_repo"] = "nabin2004/educlaw-manim-sft"
                elif stage == "traces":
                    stage_updates["dataset_repo"] = "nabin2004/AOS-Trajectories"
                    if args.dataset_file is None:
                        stage_updates["dataset_file"] = "tool_trace/train.jsonl"
                    if getattr(args, "learning_rate", None) is None:
                        stage_updates["learning_rate"] = 5e-5
                    if getattr(args, "replay_ratio", None) is None:
                        stage_updates["replay_ratio"] = 0.10
            config = replace(config, **stage_updates)
        if getattr(args, "replay_ratio", None) is not None:
            config = replace(config, replay_ratio=args.replay_ratio)
        if getattr(args, "replay_dataset", None) is not None:
            config = replace(config, replay_dataset=args.replay_dataset)
        if getattr(args, "eval_manibench", False):
            config = replace(config, eval_manibench=True)
        if getattr(args, "manibench_render", False):
            config = replace(config, manibench_render=True)
        if getattr(args, "manibench_timeout", None) is not None:
            config = replace(config, manibench_timeout=args.manibench_timeout)
        if args.output_dir is not None:
            config = replace(config, output_dir=Path(args.output_dir))
        if args.model_id is not None:
            config = replace(config, model_id=args.model_id)
        if getattr(args, "learning_rate", None) is not None:
            config = replace(config, learning_rate=args.learning_rate)
        if args.epochs is not None:
            config = replace(config, epochs=args.epochs)
        if args.seq_len is not None:
            config = replace(config, seq_len=args.seq_len)
        if args.no_4bit:
            config = replace(config, use_4bit=False)
        if getattr(args, "lora_r", None) is not None:
            config = replace(config, lora_r=args.lora_r)
        if getattr(args, "lora_alpha", None) is not None:
            config = replace(config, lora_alpha=args.lora_alpha)
        if getattr(args, "packing", False):
            config = replace(config, packing=True)
        if getattr(args, "no_packing", False):
            config = replace(config, packing=False)
        if args.report_to is not None:
            config = replace(config, report_to=args.report_to)
        if args.push_to_hub:
            config = replace(config, push_to_hub=True)
        if args.hub_model_id is not None:
            config = replace(config, hub_model_id=args.hub_model_id)
        if getattr(args, "run_name", None) is not None:
            config = replace(config, run_name=args.run_name)
        if getattr(args, "save_steps", None) is not None:
            config = replace(config, save_steps=args.save_steps)
        elif os.environ.get("SAVE_STEPS", "").strip():
            config = replace(config, save_steps=int(os.environ["SAVE_STEPS"]))
        if getattr(args, "no_resume", False):
            config = replace(config, resume="never")
        elif getattr(args, "resume", False):
            config = replace(config, resume="always")
        if getattr(args, "resume_from", None) is not None:
            config = replace(config, resume_from=Path(args.resume_from))
        elif os.environ.get("RESUME_FROM", "").strip():
            config = replace(config, resume_from=Path(os.environ["RESUME_FROM"]))
        if getattr(args, "hub_checkpoint_id", None) is not None:
            config = replace(config, hub_checkpoint_id=args.hub_checkpoint_id)
        elif os.environ.get("HUB_CHECKPOINT_ID", "").strip():
            config = replace(
                config, hub_checkpoint_id=os.environ["HUB_CHECKPOINT_ID"].strip()
            )
        if getattr(args, "no_sync_trainer_checkpoint", False):
            config = replace(config, sync_trainer_checkpoint=False)
        if not config.hub_checkpoint_id:
            config = replace(config, hub_checkpoint_id=config.hub_model_id)
        return apply_gpu_precision(config.resolve_paths())


def effective_bf16(requested: bool) -> bool:
    """Native BF16 needs Ampere+ (sm_80). P100 is sm_60; T4 is sm_75."""
    if not requested:
        return False
    try:
        import torch

        if not torch.cuda.is_available():
            return False
        major, _minor = torch.cuda.get_device_capability(0)
        if major < 8:
            return False
        if not torch.cuda.is_bf16_supported():
            return False
    except Exception:
        return requested
    return True


def apply_gpu_precision(config: TrainingConfig) -> TrainingConfig:
    """Force FP16 on Pascal/Turing (Kaggle P100/T4) even if a preset was missed."""
    try:
        import torch

        if not torch.cuda.is_available():
            return config
        major, minor = torch.cuda.get_device_capability(0)
        if major < 8 and config.use_bf16:
            print(
                f"GPU sm_{major}{minor} detected -> forcing FP16 (bf16=False)",
                file=sys.stderr,
            )
            return replace(config, use_bf16=False)
    except Exception:
        return config
    return config


def default_kaggle_output_dir() -> Path:
    override = os.environ.get("SFT_OUTPUT_DIR", "").strip()
    if override:
        return Path(override)
    kaggle_working = Path("/kaggle/working")
    if kaggle_working.is_dir() and os.access(kaggle_working, os.W_OK):
        return kaggle_working / SFT_OUTPUT_DIR_NAME
    return QWEN_ROOT / SFT_OUTPUT_DIR_NAME


def apply_rtx3060_preset(config: TrainingConfig) -> TrainingConfig:
    """NVIDIA RTX 3060 (12 GB VRAM) preset: 4-bit NF4 QLoRA, paged_adamw_8bit, bf16, batch 1, accum 8."""
    load_training_dotenv()
    report_to = config.report_to
    if report_to == "wandb" and not os.environ.get("WANDB_API_KEY", "").strip():
        report_to = "none"
    is_7b_or_larger = any(tag in config.model_id.lower() for tag in ("7b", "8b", "6.7b", "13b"))
    seq_len = 2048 if is_7b_or_larger else config.seq_len

    return replace(
        config,
        batch_size=1,
        grad_accum=8,
        seq_len=seq_len,
        use_4bit=True,
        use_bf16=True,
        num_proc=1 if sys.platform == "win32" else 4,
        packing=False,
        lora_r=16 if is_7b_or_larger else config.lora_r,
        lora_alpha=32 if is_7b_or_larger else config.lora_alpha,
        optim="paged_adamw_8bit",
        report_to=report_to,
    )


def apply_kaggle_preset(config: TrainingConfig) -> TrainingConfig:
    """P100/T4 QLoRA: 4-bit NF4, LoRA r=16, full corpus, no packing, fp16."""
    print(
        "NOTE: --kaggle QLoRA on P100/T4 (16 GB): fp16, 4-bit NF4, "
        f"lora_r=16, packing=off, full dataset (max_samples unset/0), "
        f"seq_len=2048 for {config.model_id}. Resume from checkpoint-* "
        "across sessions; Hub stores last-trainer-checkpoint.",
        file=sys.stderr,
    )
    report_to = config.report_to
    if report_to == "wandb" and not os.environ.get("WANDB_API_KEY", "").strip():
        report_to = "none"
    save_steps = config.save_steps
    env_steps = os.environ.get("SAVE_STEPS", "").strip()
    if env_steps:
        save_steps = int(env_steps)
    return replace(
        config,
        batch_size=1,
        grad_accum=8,
        seq_len=2048,
        num_proc=2,
        packing=False,
        lora_r=16,
        lora_alpha=32,
        use_bf16=False,
        optim="paged_adamw_8bit",
        save_strategy="steps",
        save_steps=save_steps,
        save_total_limit=2,
        report_to=report_to,
        output_dir=default_kaggle_output_dir(),
        sync_trainer_checkpoint=True,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Qwen2.5-Coder-7B staged SFT (manim-sft / educlaw / traces)"
    )
    parser.add_argument("--data-path", type=Path, default=None)
    parser.add_argument("--dataset-repo", default=None)
    parser.add_argument("--dataset-file", default=None)
    parser.add_argument(
        "--dataset-split",
        default=None,
        help='Hub split for native datasets (default: "train")',
    )
    parser.add_argument(
        "--init-adapter",
        type=Path,
        default=None,
        help="Continue training an existing LoRA adapter (no new peft_config)",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Optional shuffled subsample size; 0 or negative = full split",
    )
    parser.add_argument("--shuffle-seed", type=int, default=None)
    parser.add_argument(
        "--stage",
        default=None,
        choices=("manim", "educlaw", "traces"),
        help="Curriculum stage (sets W&B run name/tags)",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--model-id", default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--learning-rate", type=float, default=None)
    parser.add_argument(
        "--replay-ratio",
        type=float,
        default=None,
        help="Fraction of Phase 1 replay dataset to mix into training (e.g. 0.10 for 10%% replay)",
    )
    parser.add_argument(
        "--replay-dataset",
        default=None,
        help='HF dataset for replay buffer (default: "nabin2004/manim-sft-10k")',
    )
    parser.add_argument(
        "--eval-manibench",
        action="store_true",
        help="Evaluate on ManiBench benchmark dataset after each epoch and log to W&B",
    )
    parser.add_argument(
        "--manibench-render",
        action="store_true",
        help="Enable headless Manim video rendering during ManiBench evaluation",
    )
    parser.add_argument(
        "--manibench-timeout",
        type=int,
        default=None,
        help="Per-scene rendering timeout in seconds (default: 20)",
    )
    parser.add_argument("--seq-len", type=int, default=None)
    parser.add_argument("--no-4bit", action="store_true")
    parser.add_argument("--lora-r", type=int, default=None)
    parser.add_argument("--lora-alpha", type=int, default=None)
    parser.add_argument(
        "--packing",
        action="store_true",
        help="Pack sequences (needs Flash Attention; off on Kaggle P100)",
    )
    parser.add_argument(
        "--no-packing",
        action="store_true",
        help="Disable packing (shorter examples, more steps)",
    )
    parser.add_argument(
        "--rtx3060",
        action="store_true",
        help="NVIDIA RTX 3060 12GB preset: 4-bit NF4, paged_adamw_8bit, bf16, seq 2048/4096",
    )
    parser.add_argument(
        "--kaggle",
        action="store_true",
        help="P100/T4 QLoRA: 4-bit, r=16, full dataset, packing off, seq 2048",
    )
    parser.add_argument("--report-to", default=None)
    parser.add_argument("--run-name", default=None)
    parser.add_argument("--push-to-hub", action="store_true")
    parser.add_argument("--hub-model-id", default=None)
    parser.add_argument(
        "--hub-checkpoint-id",
        default=None,
        help="Hub repo for Trainer checkpoints (default: --hub-model-id)",
    )
    parser.add_argument(
        "--save-steps",
        type=int,
        default=None,
        help="Checkpoint every N steps (Kaggle default 200; env SAVE_STEPS)",
    )
    resume = parser.add_mutually_exclusive_group()
    resume.add_argument(
        "--resume",
        action="store_true",
        help="Require a Trainer checkpoint and continue from it",
    )
    resume.add_argument(
        "--no-resume",
        action="store_true",
        help="Start from step 0 even if checkpoint-* exists",
    )
    parser.add_argument(
        "--resume-from",
        type=Path,
        default=None,
        help="Directory with checkpoint-* (or a checkpoint dir). Env RESUME_FROM",
    )
    parser.add_argument(
        "--no-sync-trainer-checkpoint",
        action="store_true",
        help="Do not upload/download last-trainer-checkpoint on the Hub",
    )
    parser.add_argument("--smoke", action="store_true", help="Tiny overfit smoke run")
    return parser
