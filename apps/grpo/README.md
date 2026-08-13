# GRPO — ManiBench Phase 2

Reinforcement fine-tuning (GRPO) on [ManiBench](https://huggingface.co/datasets/nabin2004/ManiBench) after Phase 1 SFT. Stacks a trainable GRPO LoRA on top of a frozen SFT adapter.

Supports **Gemma 4** (Unsloth FastVisionModel) and **Qwen2.5-Coder-7B** (transformers CausalLM).

## Workflow

```text
Phase 1 SFT  →  adapter  →  Phase 2 GRPO  →  package_adapter.py (merge + GGUF + HF)
```

## Usage

```bash
cd apps/grpo
uv sync

# Gemma (default)
uv run python run.py --smoke
uv run python run.py --sft-lora ../sft/gemma4-31b-manim-ft

# Qwen
uv run python run.py --base qwen --sft-lora ../qwenCoder/qwen2.5-coder-7b-manim-ft --smoke
uv run python run.py --base qwen \
  --prompts-path ../agents/sft_data_gen/prompts_curriculum_200.jsonl \
  --repeat-factor 2

# Package GRPO adapter → merge → llama.cpp GGUF → Hub
uv run python package_adapter.py --base qwen --adapter-dir ./grpo_qwen_manim --push-to-hub
```

## Layout

| Module | Role |
|--------|------|
| [`config.py`](config.py) | `TrainingConfig`, CLI (`--base gemma|qwen`) |
| [`manibench.py`](manibench.py) | ManiBench pilot **or** trajectory prompt JSONL |
| [`model.py`](model.py) | Gemma Unsloth path / Qwen CausalLM+PEFT path |
| [`trainer.py`](trainer.py) | GRPO trainer |
| [`rewards.py`](rewards.py) | exec / align / vcer / coverage |
| [`package_adapter.py`](package_adapter.py) | Shared merge + GGUF + HF push |
| [`run.py`](run.py) | CLI entrypoint |

## Dataset

- Default: `ManiBench_Pilot_Dataset.json` from HF
- Alternate: `--prompts-path` JSONL with `prompt` / `user_prompt` fields (AOS trajectory bank)

## Weights & Biases

Defaults to **wandb** (project `aos-grpo`). Disable with `--report-to none`.
