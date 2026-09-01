from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

from peft import LoraConfig
from trl import SFTConfig

SFT_ROOT = Path(__file__).resolve().parent
TRAINING_ROOT = SFT_ROOT.parent / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from model_identity import (  # noqa: E402
    BASE_MODEL_ID,
    HUB_SFT_REPO,
    SFT_OUTPUT_DIR_NAME,
    WANDB_RUN_GROUP,
    WANDB_SFT_RUN_NAME,
    WANDB_TAGS,
)

LANGUAGE_MODEL_LORA_TARGETS = (
    r".*\.language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)"
)


@dataclass
class TrainingConfig:
    model_id: str = BASE_MODEL_ID
    dataset_repo: str = "nabin2004/manim-sft"
    dataset_file: str = "data/train.jsonl"
    data_path: Path | None = None
    output_dir: Path = SFT_ROOT / SFT_OUTPUT_DIR_NAME
    use_4bit: bool = True
    seq_len: int = 8192
    epochs: int = 1
    batch_size: int = 1
    grad_accum: int = 8
    learning_rate: float = 5e-6
    num_proc: int = 8
    report_to: str = "wandb"
    run_name: str = WANDB_SFT_RUN_NAME
    wandb_project: str = "aos-sft"
    wandb_group: str = WANDB_RUN_GROUP
    wandb_tags: tuple[str, ...] = field(default_factory=lambda: WANDB_TAGS)
    attn_implementation: str = "eager"
    device_map: str | dict[str, int] = "auto"
    strip_multimodal_towers: bool = False
    packing: bool = False
    assistant_only_loss: bool = True
    use_liger_kernel: bool = False
    push_to_hub: bool = False
    hub_model_id: str = HUB_SFT_REPO
    hub_private: bool = False
    eval_manibench: bool = False
    manibench_render: bool = False
    manibench_timeout: int = 20

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
            target_modules=LANGUAGE_MODEL_LORA_TARGETS,
            bias="none",
            task_type="CAUSAL_LM",
            modules_to_save=["embed_tokens", "lm_head"],
            ensure_weight_tying=True,
        )

    def sft_config(self) -> SFTConfig:
        logging_dir = os.environ.get("AIP_TENSORBOARD_LOG_DIR") or None
        sft_kwargs: dict = {
            "output_dir": str(self.output_dir),
            "logging_dir": logging_dir,
            "num_train_epochs": self.epochs,
            "per_device_train_batch_size": self.batch_size,
            "gradient_accumulation_steps": self.grad_accum,
            "gradient_checkpointing": True,
            "gradient_checkpointing_kwargs": {"use_reentrant": False},
            "use_cache": False,
            "learning_rate": self.learning_rate,
            "lr_scheduler_type": "cosine",
            "warmup_steps": 10,
            "optim": "adamw_torch_fused",
            "bf16": True,
            "logging_steps": 10,
            "save_strategy": "epoch",
            "packing": self.packing,
            "max_length": self.seq_len,
            "assistant_only_loss": self.assistant_only_loss,
            "dataset_kwargs": {"add_special_tokens": False},
            "report_to": self.report_to,
            "run_name": self.run_name,
        }
        if self.use_liger_kernel and _liger_kernel_available():
            sft_kwargs["use_liger_kernel"] = True
        return SFTConfig(**sft_kwargs)

    @classmethod
    def from_cli(cls, args: argparse.Namespace) -> TrainingConfig:
        config = cls().resolve_paths()
        if getattr(args, "rtx3060", False):
            config = apply_rtx3060_preset(config)
        if args.kaggle or os.environ.get("KAGGLE_KERNEL_RUN_TYPE"):
            config = apply_kaggle_preset(config)
        if args.runpod:
            config = apply_runpod_preset(config)
        if args.colab or is_colab_runtime():
            config = apply_colab_preset(config)
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
        if args.seq_len is not None:
            config = replace(config, seq_len=args.seq_len)
        if args.grad_accum is not None:
            config = replace(config, grad_accum=args.grad_accum)
        if args.device_map is not None:
            config = replace(config, device_map=_parse_device_map(args.device_map))
        if args.no_strip_towers:
            config = replace(config, strip_multimodal_towers=False)
        if args.attn_implementation is not None:
            config = replace(config, attn_implementation=args.attn_implementation)
        if args.use_liger_kernel:
            config = replace(config, use_liger_kernel=True)
        if args.push_to_hub:
            config = replace(config, push_to_hub=True)
        if args.hub_model_id is not None:
            config = replace(config, hub_model_id=args.hub_model_id)
        if args.hub_private:
            config = replace(config, hub_private=True)
        if getattr(args, "eval_manibench", False):
            config = replace(config, eval_manibench=True)
        if getattr(args, "manibench_render", False):
            config = replace(config, manibench_render=True)
        if getattr(args, "manibench_timeout", None) is not None:
            config = replace(config, manibench_timeout=args.manibench_timeout)
        if args.run_name is not None:
            config = replace(config, run_name=args.run_name)
        return apply_vertex_env(config)


def _liger_kernel_available() -> bool:
    try:
        import liger_kernel  # noqa: F401

        return True
    except ImportError:
        return False


def apply_rtx3060_preset(config: TrainingConfig) -> TrainingConfig:
    """NVIDIA RTX 3060 (12 GB VRAM) optimized preset (batch 1, grad accum 8, seq 2048, 4-bit QLoRA)."""
    report_to = config.report_to
    if report_to == "wandb" and not os.environ.get("WANDB_API_KEY", "").strip():
        report_to = "none"
    return replace(
        config,
        batch_size=1,
        grad_accum=8,
        seq_len=2048 if config.seq_len == 8192 else config.seq_len,
        use_4bit=True,
        num_proc=4,
        device_map={"": 0},
        strip_multimodal_towers=True,
        packing=False,
        report_to=report_to,
    )


def apply_kaggle_preset(config: TrainingConfig) -> TrainingConfig:
    if config.model_id == BASE_MODEL_ID:
        print(
            "WARNING: --kaggle/--colab presets target T4 GPUs and are not suitable "
            f"for {BASE_MODEL_ID} (needs ~80GB VRAM). Use RunPod A100 80GB+ "
            "(--runpod), Vertex ultragpu, or a local A100 80GB+ instead.",
            file=sys.stderr,
        )
    report_to = config.report_to
    if report_to == "wandb" and not os.environ.get("WANDB_API_KEY", "").strip():
        report_to = "none"
    return replace(
        config,
        batch_size=1,
        grad_accum=8,
        seq_len=2048,
        num_proc=2,
        device_map={"": 0},
        strip_multimodal_towers=True,
        packing=False,
        attn_implementation="eager",
        report_to=report_to,
    )


def default_runpod_output_dir() -> Path:
    workspace = Path("/workspace")
    if workspace.is_dir() and os.access(workspace, os.W_OK):
        return workspace / SFT_OUTPUT_DIR_NAME
    return Path.cwd() / SFT_OUTPUT_DIR_NAME


def apply_runpod_preset(config: TrainingConfig) -> TrainingConfig:
    """A100 80GB+ defaults: full seq_len 8192, output under /workspace."""
    if config.model_id == BASE_MODEL_ID:
        print(
            "NOTE: --runpod targets A100 80GB+ (~80GB VRAM for "
            f"{BASE_MODEL_ID} 4-bit LoRA at seq 8192). "
            "On smaller GPUs pass --seq-len 2048.",
            file=sys.stderr,
        )
    report_to = config.report_to
    if report_to == "wandb" and not os.environ.get("WANDB_API_KEY", "").strip():
        report_to = "none"
    return replace(
        config,
        # Keep TrainingConfig defaults: seq_len=8192, batch_size=1, grad_accum=8, packing=False
        device_map={"": 0},
        strip_multimodal_towers=True,
        report_to=report_to,
        output_dir=default_runpod_output_dir(),
    )


COLAB_DRIVE_ROOT = Path("/content/drive/MyDrive")


def is_colab_runtime() -> bool:
    return bool(os.environ.get("COLAB_RELEASE_TAG"))


def default_colab_output_dir() -> Path:
    override = os.environ.get("SFT_OUTPUT_DIR", "").strip()
    if override:
        return Path(override)
    drive_out = COLAB_DRIVE_ROOT / SFT_OUTPUT_DIR_NAME
    if COLAB_DRIVE_ROOT.is_dir() and os.access(COLAB_DRIVE_ROOT, os.W_OK):
        return drive_out
    return Path(f"/content/{SFT_OUTPUT_DIR_NAME}")


def apply_colab_preset(config: TrainingConfig) -> TrainingConfig:
    config = apply_kaggle_preset(config)
    return replace(config, output_dir=default_colab_output_dir())


def _parse_device_map(value: str) -> str | dict[str, int]:
    if value == "auto":
        return "auto"
    if value.isdigit():
        return {"": int(value)}
    raise argparse.ArgumentTypeError(
        f'Invalid device map "{value}". Use "auto" or a GPU index like "0".'
    )


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
        description="Fine-tune Gemma 4 on Manim instruction chat pairs"
    )
    parser.add_argument(
        "--data-path",
        default=None,
        help="Local trajectory JSONL override (default: Hugging Face dataset)",
    )
    parser.add_argument(
        "--dataset-repo",
        default=None,
        help='HF dataset id (default: "nabin2004/manim-sft")',
    )
    parser.add_argument(
        "--dataset-file",
        default=None,
        help='File within HF dataset repo (default: "data/train.jsonl")',
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for adapter weights and tokenizer",
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help=f'Hugging Face model id (default: "{BASE_MODEL_ID}")',
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
    parser.add_argument(
        "--rtx3060",
        action="store_true",
        help="Apply RTX 3060 12GB VRAM optimized defaults (batch 1, grad accum 8, seq 2048, 4-bit QLoRA)",
    )
    parser.add_argument(
        "--kaggle",
        action="store_true",
        help="Apply Kaggle T4-friendly defaults (batch 1, seq 2048, GPU 0)",
    )
    parser.add_argument(
        "--runpod",
        action="store_true",
        help="Apply RunPod A100/workspace defaults (seq 8192, output under /workspace)",
    )
    parser.add_argument(
        "--colab",
        action="store_true",
        help="Apply Colab defaults (GPU-safe settings, output under Google Drive)",
    )
    parser.add_argument(
        "--seq-len",
        type=int,
        default=None,
        help="Max sequence length for SFT packing (default: 8192, 2048 with --kaggle)",
    )
    parser.add_argument(
        "--grad-accum",
        type=int,
        default=None,
        help="Gradient accumulation steps",
    )
    parser.add_argument(
        "--device-map",
        default=None,
        help='Device map for model load ("auto" or GPU index like "0")',
    )
    parser.add_argument(
        "--no-strip-towers",
        action="store_true",
        help="Keep vision/audio towers loaded (uses more VRAM)",
    )
    parser.add_argument(
        "--attn-implementation",
        choices=("eager", "sdpa", "flash_attention_2"),
        default=None,
        help='Attention backend (default: "eager" for Gemma 4 unified arch)',
    )
    parser.add_argument(
        "--use-liger-kernel",
        action="store_true",
        help="Enable liger-kernel fused ops in SFTTrainer (requires optional extra)",
    )
    parser.add_argument(
        "--push-to-hub",
        action="store_true",
        help="Upload LoRA adapter to Hugging Face Hub after training",
    )
    parser.add_argument(
        "--hub-model-id",
        default=None,
        help=f'HF model repo id for adapter upload (default: "{HUB_SFT_REPO}")',
    )
    parser.add_argument(
        "--hub-private",
        action="store_true",
        help="Create/upload the Hub model repo as private",
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
    parser.add_argument(
        "--run-name",
        default=None,
        help=f'W&B run name (default: "{WANDB_SFT_RUN_NAME}")',
    )
    return parser
