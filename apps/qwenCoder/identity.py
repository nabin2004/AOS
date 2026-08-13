"""Shared naming for AOS Qwen2.5-Coder Manim finetuning artifacts."""

from __future__ import annotations

BASE_MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"

SFT_OUTPUT_DIR_NAME = "qwen2.5-coder-7b-manim-ft"
MERGED_OUTPUT_DIR_NAME = "qwen2.5-coder-7b-manim-merged"
GGUF_OUTPUT_DIR_NAME = "qwen2.5-coder-7b-manim-gguf"
DPO_OUTPUT_DIR_NAME = "qwen2.5-coder-7b-manim-dpo"
GRPO_OUTPUT_DIR_NAME = "qwen2.5-coder-7b-manim-grpo"

HUB_SFT_REPO = "nabin2004/AOS-qwen2.5-coder-7b-manim-sft"
HUB_MERGED_REPO = "nabin2004/AOS-qwen2.5-coder-7b-manim-merged"
HUB_GGUF_REPO = "nabin2004/AOS-qwen2.5-coder-7b-manim-gguf"
HUB_DPO_REPO = "nabin2004/AOS-qwen2.5-coder-7b-manim-dpo"
HUB_DATASET_REPO = "nabin2004/AOS-Qwen-Trajectories"

OLLAMA_MODEL_TAG = "aos-qwen2.5-coder-7b-manim"
OLLAMA_BASE_TAG = "qwen2.5-coder:7b"

WANDB_SFT_RUN_NAME = "qwen2.5-coder-7b-manim-sft"
WANDB_DPO_RUN_NAME = "qwen2.5-coder-7b-manim-dpo"
WANDB_GRPO_RUN_NAME = "qwen2.5-coder-7b-manim-grpo"
WANDB_RUN_GROUP = "qwen2.5-coder-7b-manim"
WANDB_TAGS = ("qwen2.5-coder-7b", "manim", "aos")

# Staged curriculum identifiers used by train_stages.sh / --stage
STAGE_MANIM = "manim"
STAGE_EDUCLAW = "educlaw"
STAGE_TRACES = "traces"
STAGE_DPO = "dpo"
STAGE_GRPO = "grpo"

STAGE_RUN_NAMES: dict[str, str] = {
    STAGE_MANIM: "qwen2.5-coder-7b-manim-sft-manim",
    STAGE_EDUCLAW: "qwen2.5-coder-7b-manim-sft-educlaw",
    STAGE_TRACES: "qwen2.5-coder-7b-manim-sft-traces",
    STAGE_DPO: WANDB_DPO_RUN_NAME,
    STAGE_GRPO: WANDB_GRPO_RUN_NAME,
}

STAGE_TAGS: dict[str, tuple[str, ...]] = {
    STAGE_MANIM: ("sft", "manim-sft"),
    STAGE_EDUCLAW: ("sft", "educlaw"),
    STAGE_TRACES: ("sft", "tool-trace"),
    STAGE_DPO: ("dpo", "preference"),
    STAGE_GRPO: ("grpo", "manibench"),
}


def stage_run_name(stage: str | None) -> str:
    if not stage:
        return WANDB_SFT_RUN_NAME
    return STAGE_RUN_NAMES.get(stage, f"qwen2.5-coder-7b-manim-sft-{stage}")


def stage_tags(stage: str | None) -> tuple[str, ...]:
    base = WANDB_TAGS
    if not stage:
        return (*base, "sft")
    extra = STAGE_TAGS.get(stage, ("sft", stage))
    return (*base, *extra)
