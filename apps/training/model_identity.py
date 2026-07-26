"""Shared model and artifact naming for AOS SFT, GRPO, serving, and W&B."""

from __future__ import annotations

BASE_MODEL_ID = "google/gemma-4-31B-it"
LEGACY_BASE_MODEL_ID = "google/gemma-4-E2B-it"

SFT_OUTPUT_DIR_NAME = "gemma4-31b-manim-ft"
MERGED_OUTPUT_DIR_NAME = "gemma4-31b-manim-merged"
GGUF_OUTPUT_DIR_NAME = "gemma4-31b-manim-gguf"

HUB_SFT_REPO = "nabin2004/AOS-gemma4-31b-manim-sft"
HUB_MERGED_REPO = "nabin2004/AOS-gemma4-31b-manim-merged"
HUB_GGUF_REPO = "nabin2004/AOS-gemma4-31b-manim-gguf"

OLLAMA_MODEL_TAG = "aos-gemma4-31b-manim"
OLLAMA_HF_GGUF_REF = f"huggingface.co/{HUB_GGUF_REPO}:Q4_K_M"

WANDB_SFT_RUN_NAME = "gemma4-31b-manim-sft"
WANDB_GRPO_RUN_NAME = "gemma4-31b-manim-grpo"
WANDB_RUN_GROUP = "gemma4-31b-manim"
WANDB_TAGS = ("gemma4-31b", "manim", "aos")

VERTEX_SFT_DISPLAY_NAME = "aos-sft-gemma4-31b-manim"
