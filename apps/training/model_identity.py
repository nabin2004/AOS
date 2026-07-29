"""Shared model and artifact naming for AOS SFT, GRPO, serving, and W&B."""

from __future__ import annotations

BASE_MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"
LEGACY_BASE_MODEL_ID = "google/gemma-4-31B-it"
# Serving / GRPO stay on Gemma until Ollama/vLLM paths are migrated.
SERVING_MODEL_ID = LEGACY_BASE_MODEL_ID

SFT_OUTPUT_DIR_NAME = "qwen25-coder-7b-manim-ft"
MERGED_OUTPUT_DIR_NAME = "qwen25-coder-7b-manim-merged"
GGUF_OUTPUT_DIR_NAME = "qwen25-coder-7b-manim-gguf"

HUB_SFT_REPO = "nabin2004/AOS-qwen25-coder-7b-manim-sft"
HUB_MERGED_REPO = "nabin2004/AOS-qwen25-coder-7b-manim-merged"
HUB_GGUF_REPO = "nabin2004/AOS-qwen25-coder-7b-manim-gguf"

OLLAMA_MODEL_TAG = "aos-qwen25-coder-7b-manim"
OLLAMA_HF_GGUF_REF = f"huggingface.co/{HUB_GGUF_REPO}:Q4_K_M"

# Live Ollama / agent hybrid profile until the Qwen GGUF is published.
LEGACY_HUB_GGUF_REPO = "nabin2004/AOS-gemma4-31b-manim-gguf"
LEGACY_OLLAMA_MODEL_TAG = "aos-gemma4-31b-manim"
LEGACY_OLLAMA_HF_GGUF_REF = f"huggingface.co/{LEGACY_HUB_GGUF_REPO}:Q4_K_M"
SERVING_OLLAMA_MODEL_TAG = LEGACY_OLLAMA_MODEL_TAG
SERVING_OLLAMA_HF_GGUF_REF = LEGACY_OLLAMA_HF_GGUF_REF

WANDB_SFT_RUN_NAME = "qwen25-coder-7b-manim-sft"
WANDB_GRPO_RUN_NAME = "qwen25-coder-7b-manim-grpo"
WANDB_RUN_GROUP = "qwen25-coder-7b-manim"
WANDB_TAGS = ("qwen25-coder-7b", "manim", "aos")

VERTEX_SFT_DISPLAY_NAME = "aos-sft-qwen25-coder-7b-manim"
