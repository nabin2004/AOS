# GRPO — ManiBench Phase 2

Reinforcement fine-tuning (GRPO) on [ManiBench](https://huggingface.co/datasets/nabin2004/ManiBench) after Phase 1 SFT (and optional DPO). Stacks a trainable GRPO LoRA on top of a frozen policy adapter.

Supports **Gemma 4** (Unsloth FastVisionModel) and **Qwen2.5-Coder-7B** (transformers CausalLM).

ManiBench is the **structure reference** for GRPO: each problem supplies `full_prompt`, `required_visual_events`, `coverage_requirements`, and `version_conflict_notes` used by [`rewards.py`](rewards.py).

## Workflow

```text
Phase 1 SFT (+ DPO for Qwen)  →  frozen adapter  →  Phase 2 GRPO (ManiBench)  →  package_adapter.py
```

### Qwen staged chain

See [`apps/qwenCoder/train_stages.sh`](../qwenCoder/train_stages.sh):

```text
manim-sft → educlaw (20k) → AOS-Trajectories → DPO → GRPO ManiBench
```

When `--base qwen` and `--sft-lora` is omitted, GRPO prefers `../dpo/qwen2.5-coder-7b-manim-dpo` if that directory exists, else `../qwenCoder/qwen2.5-coder-7b-manim-ft`.

## Usage

```bash
cd apps/grpo
uv sync

# Gemma (default)
uv run python run.py --smoke
uv run python run.py --sft-lora ../sft/gemma4-31b-manim-ft

# Qwen — ManiBench by default (no --prompts-path)
uv run python run.py --base qwen --smoke
uv run python run.py --base qwen \
  --sft-lora ../dpo/qwen2.5-coder-7b-manim-dpo

# Optional prompt-bank override (not ManiBench structure)
uv run python run.py --base qwen \
  --prompts-path ../agents/sft_data_gen/prompts_curriculum_200.jsonl \
  --repeat-factor 2

# Package GRPO adapter → merge → llama.cpp GGUF → Hub
uv run python package_adapter.py --base qwen --adapter-dir ./grpo_qwen_manim --push-to-hub
```

## Layout

| Module | Role |
|--------|------|
| [`config.py`](config.py) | `TrainingConfig`, CLI (`--base gemma\|qwen`) |
| [`manibench.py`](manibench.py) | ManiBench pilot **or** trajectory prompt JSONL |
| [`model.py`](model.py) | Gemma Unsloth path / Qwen CausalLM+PEFT path |
| [`trainer.py`](trainer.py) | GRPO trainer |
| [`rewards.py`](rewards.py) | exec / align (blended lexical + live OpenCLIP) / vcer / coverage |
| [`package_adapter.py`](package_adapter.py) | Shared merge + GGUF + HF push |
| [`run.py`](run.py) | CLI entrypoint |

## Dataset & Reward Pipeline

- Default: `ManiBench_Pilot_Dataset.json` from HF (`nabin2004/ManiBench`) or `data/splits/train.jsonl` from `nabin2004/Manim-grpo-dataset-200`.
- Alternate: `--prompts-path` JSONL with `prompt` / `user_prompt` fields (AOS trajectory bank).

### Reward Mix & Two-Stage Vision Pipeline:
- **Executability (50%)**: Syntax verification + Scene class inheritance; hard gate ($R=0.0$ if unexecutable). When `MANIBENCH_GRPO_RENDER=1`, renders headless Manim video.
- **Alignment (25%)**: 
  - *Stage 1*: Fast AST lexical pattern match against `visual_events.json`.
  - *Stage 2*: When `MANIBENCH_GRPO_CLIP_REWARD=1`, executes live **OpenCLIP ViT-B-32** frame extraction at 2 FPS on rendered video, scoring temporal event windows against `clip_query` strings.
- **VCER (15%)**: Penalty for deprecated ManimGL constructs breaking in Manim CE.
- **Coverage (10%)**: Multi-dimensional term density across Math, Visual, Numeric, and Structural axes.
- **Length penalty**: Subtracted from combined score.

## Weights & Biases

Defaults to **wandb** (project `aos-grpo`). Configure via [`apps/training/.env.example`](../training/.env.example). Qwen runs use group `qwen2.5-coder-7b-manim` and tags `qwen2.5-coder-7b,manim,aos,grpo,manibench`. Disable with `--report-to none`.
