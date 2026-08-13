from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, replace
from pathlib import Path

GRPO_ROOT = Path(__file__).resolve().parent
TRAINING_ROOT = GRPO_ROOT.parent / "training"
if str(TRAINING_ROOT) not in sys.path:
    sys.path.insert(0, str(TRAINING_ROOT))

from model_identity import (  # noqa: E402
    BASE_MODEL_ID,
    SFT_OUTPUT_DIR_NAME,
    WANDB_GRPO_RUN_NAME,
    WANDB_RUN_GROUP,
    WANDB_TAGS,
)

DEFAULT_BASE_MODEL = BASE_MODEL_ID
DEFAULT_LEARNING_RATE = 1e-4
DEFAULT_BETA = 0.001
DEFAULT_LENGTH_PENALTY_COEF = 0.001
GRPO_ADAPTER = "grpo"


@dataclass
class TrainingConfig:
    sft_lora_path: Path = GRPO_ROOT / ".." / "sft" / SFT_OUTPUT_DIR_NAME
    base_model: str | None = None
    base_family: str = "gemma"  # gemma | qwen
    dataset_repo: str = "nabin2004/ManiBench"
    dataset_path: Path | None = None
    prompts_path: Path | None = None
    output_dir: Path = GRPO_ROOT / "grpo_manim"
    repeat_factor: int = 50
    max_seq_length: int = 2048
    max_prompt_length: int = 1024
    max_completion_length: int = 512
    num_generations: int = 4
    learning_rate: float = DEFAULT_LEARNING_RATE
    beta: float = DEFAULT_BETA
    load_in_4bit: bool = True
    smoke: bool = False
    max_steps: int | None = None
    grpo_only: bool = False
    render: bool = False
    no_render: bool = False
    reward_debug: bool = False
    length_penalty: float = DEFAULT_LENGTH_PENALTY_COEF
    report_to: str = "wandb"
    run_name: str = WANDB_GRPO_RUN_NAME
    wandb_project: str = "aos-grpo"
    wandb_group: str = WANDB_RUN_GROUP
    wandb_tags: tuple[str, ...] = WANDB_TAGS

    def resolve_paths(self) -> TrainingConfig:
        dataset_path = self.dataset_path
        if dataset_path is not None:
            dataset_path = _resolve_path(dataset_path)
        prompts_path = self.prompts_path
        if prompts_path is not None:
            prompts_path = _resolve_path(prompts_path)
        return replace(
            self,
            sft_lora_path=_resolve_path(self.sft_lora_path),
            output_dir=_resolve_path(self.output_dir),
            dataset_path=dataset_path,
            prompts_path=prompts_path,
        )

    def apply_env(self) -> None:
        os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

        if self.render:
            os.environ["MANIBENCH_GRPO_RENDER"] = "1"
        elif self.no_render:
            os.environ["MANIBENCH_GRPO_RENDER"] = "0"
        elif "MANIBENCH_GRPO_RENDER" not in os.environ:
            os.environ["MANIBENCH_GRPO_RENDER"] = "0"

        if self.reward_debug:
            os.environ["MANIBENCH_GRPO_REWARD_DEBUG"] = "1"

        os.environ["MANIBENCH_LENGTH_PENALTY_COEF"] = str(self.length_penalty)

    @classmethod
    def from_cli(cls, args: argparse.Namespace) -> TrainingConfig:
        config = cls().resolve_paths()
        if args.sft_lora is not None:
            config = replace(config, sft_lora_path=_resolve_path(Path(args.sft_lora)))
        if args.base is not None:
            family = str(args.base).lower().strip()
            if family not in ("gemma", "qwen"):
                raise SystemExit(f"Unsupported --base {args.base!r}; use gemma|qwen")
            config = replace(config, base_family=family)
            if family == "qwen":
                qwen_sft = GRPO_ROOT / ".." / "qwenCoder" / "qwen2.5-coder-7b-manim-ft"
                qwen_dpo = GRPO_ROOT / ".." / "dpo" / "qwen2.5-coder-7b-manim-dpo"
                # Prefer DPO adapter as the frozen stack base when present.
                qwen_default = qwen_dpo if qwen_dpo.is_dir() else qwen_sft
                updates: dict = {
                    "run_name": "qwen2.5-coder-7b-manim-grpo",
                    "wandb_group": "qwen2.5-coder-7b-manim",
                    "wandb_tags": (
                        "qwen2.5-coder-7b",
                        "manim",
                        "aos",
                        "grpo",
                        "manibench",
                    ),
                }
                if args.base_model is None:
                    updates["base_model"] = "Qwen/Qwen2.5-Coder-7B-Instruct"
                if args.sft_lora is None:
                    updates["sft_lora_path"] = _resolve_path(qwen_default)
                if args.output_dir is None:
                    updates["output_dir"] = _resolve_path(
                        GRPO_ROOT / "grpo_qwen_manim"
                    )
                config = replace(config, **updates)
        if args.base_model is not None:
            config = replace(config, base_model=args.base_model)
        if args.dataset_path is not None:
            config = replace(
                config, dataset_path=_resolve_path(Path(args.dataset_path))
            )
        if args.prompts_path is not None:
            config = replace(
                config, prompts_path=_resolve_path(Path(args.prompts_path))
            )
        if args.output_dir is not None:
            config = replace(config, output_dir=_resolve_path(Path(args.output_dir)))
        if args.repeat_factor is not None:
            config = replace(config, repeat_factor=args.repeat_factor)
        if args.max_seq_length is not None:
            config = replace(config, max_seq_length=args.max_seq_length)
        if args.max_prompt_length is not None:
            config = replace(config, max_prompt_length=args.max_prompt_length)
        if args.max_completion_length is not None:
            config = replace(config, max_completion_length=args.max_completion_length)
        if args.num_generations is not None:
            config = replace(config, num_generations=args.num_generations)
        if args.max_steps is not None:
            config = replace(config, max_steps=args.max_steps)
        if args.length_penalty is not None:
            config = replace(config, length_penalty=args.length_penalty)
        if args.full_precision:
            config = replace(config, load_in_4bit=False)
        if args.smoke:
            config = replace(config, smoke=True)
        if args.grpo_only:
            config = replace(config, grpo_only=True)
        if args.render:
            config = replace(config, render=True)
        if args.no_render:
            config = replace(config, no_render=True)
        if args.reward_debug:
            config = replace(config, reward_debug=True)
        if args.report_to is not None:
            config = replace(config, report_to=args.report_to)
        if args.run_name is not None:
            config = replace(config, run_name=args.run_name)
        return apply_vertex_env(config)


def apply_vertex_env(config: TrainingConfig) -> TrainingConfig:
    model_dir = os.environ.get("AIP_MODEL_DIR", "").strip()
    if model_dir:
        config = replace(config, output_dir=Path(model_dir))
    return config


def hub_token() -> str | None:
    raw = os.environ.get("HF_TOKEN", "")
    return raw.strip() or None


def _resolve_path(path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (Path.cwd() / path).resolve()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="GRPO Manim training on ManiBench (Unsloth Gemma-4 stacked LoRA)",
    )
    parser.add_argument(
        "--sft-lora",
        default=None,
        help=f"SFT LoRA path (default: ../sft/{SFT_OUTPUT_DIR_NAME})",
    )
    parser.add_argument(
        "--base",
        choices=("gemma", "qwen"),
        default=None,
        help="Base model family (default: gemma). qwen uses CausalLM + PEFT path.",
    )
    parser.add_argument(
        "--base-model",
        default=None,
        help="Override base model (default: read from SFT adapter_config.json)",
    )
    parser.add_argument(
        "--dataset-path",
        default=None,
        help="Local ManiBench_Pilot_Dataset.json (default: download from HF)",
    )
    parser.add_argument(
        "--prompts-path",
        default=None,
        help="Optional JSONL of {prompt|user_prompt} rows instead of ManiBench",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for GRPO adapter",
    )
    parser.add_argument(
        "--repeat-factor",
        type=int,
        default=None,
        help="Repeat each ManiBench problem N times (default: 50)",
    )
    parser.add_argument(
        "--max-seq-length",
        type=int,
        default=None,
        help="Model context window for Unsloth load (default: 2048)",
    )
    parser.add_argument(
        "--max-prompt-length",
        type=int,
        default=None,
        help="Truncate prompts to this many tokens (default: 1024)",
    )
    parser.add_argument(
        "--max-completion-length",
        type=int,
        default=None,
        help="Cap completion tokens (default: 512)",
    )
    parser.add_argument(
        "--num-generations",
        type=int,
        default=None,
        help="GRPO samples per prompt (default: 4)",
    )
    parser.add_argument(
        "--full-precision",
        action="store_true",
        help="Load base in 16-bit instead of 4-bit",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="One GRPO step for GPU smoke test",
    )
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Heuristic-only executability reward (default)",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Run manim subprocess in executability reward (slow)",
    )
    parser.add_argument(
        "--grpo-only",
        action="store_true",
        help="Train GRPO LoRA on base only (skip frozen SFT adapter)",
    )
    parser.add_argument(
        "--reward-debug",
        action="store_true",
        help="Print per-step reward stats to stderr",
    )
    parser.add_argument(
        "--length-penalty",
        type=float,
        default=None,
        help=f"Length penalty coefficient (default: {DEFAULT_LENGTH_PENALTY_COEF})",
    )
    parser.add_argument(
        "--report-to",
        default=None,
        help='Logging backend (default: "wandb"; use "none" to disable)',
    )
    parser.add_argument(
        "--run-name",
        default=None,
        help=f'W&B run name (default: "{WANDB_GRPO_RUN_NAME}")',
    )
    return parser
