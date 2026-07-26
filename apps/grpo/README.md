# GRPO — ManiBench Phase 2

Reinforcement fine-tuning (GRPO) on [ManiBench](https://huggingface.co/datasets/nabin2004/ManiBench) after Phase 1 SFT. Stacks a trainable GRPO LoRA on top of a frozen SFT adapter (Gemma 4 31B via Unsloth).

## Workflow

```text
Phase 1 (apps/sft)  →  ../sft/gemma4-31b-manim-ft  →  Phase 2 (apps/grpo)  →  grpo_manim/
```

## Layout

| Module | Role |
|--------|------|
| [`config.py`](config.py) | `TrainingConfig`, CLI parser, env setup |
| [`manibench.py`](manibench.py) | Load pilot JSON from HF, build dataset, reward metadata |
| [`model.py`](model.py) | Unsloth load + frozen SFT + trainable GRPO LoRA |
| [`trainer.py`](trainer.py) | Prompt truncation, `GRPOConfig`, train/save |
| [`rewards.py`](rewards.py) | ManiBench exec / align / vcer / coverage rewards |
| [`run.py`](run.py) | CLI entrypoint |

## Dataset

Training uses `ManiBench_Pilot_Dataset.json` (12 problems) from the HuggingFace repo — **not** `load_dataset("nabin2004/ManiBench")` directly (mixed JSONL schemas break the viewer).

Each problem is repeated `repeat_factor` times (default 50 → 600 rows).

## Usage

```bash
cd apps/grpo
uv sync

# GPU smoke test (1 GRPO step)
uv run python run.py --smoke

# Full training with local SFT adapter
uv run python run.py --sft-lora ../sft/gemma4-31b-manim-ft

# Offline dataset
uv run python run.py --dataset-path ./ManiBench_Pilot_Dataset.json
```

### CLI flags

| Flag | Description |
|------|-------------|
| `--sft-lora` | SFT adapter path (default: `../sft/gemma4-31b-manim-ft`) |
| `--dataset-path` | Local pilot JSON override |
| `--output-dir` | GRPO adapter output (default: `./grpo_manim`) |
| `--repeat-factor` | Upsample factor per problem (default: 50) |
| `--smoke` | One GRPO step |
| `--render` | Run manim in exec reward (slow) |
| `--no-render` | Heuristic exec only (default) |
| `--grpo-only` | Skip frozen SFT stack |
| `--full-precision` | 16-bit instead of 4-bit |
| `--report-to` | Logging backend (`wandb` default; use `none` to disable) |
| `--run-name` | W&B run name (default: `gemma4-31b-manim-grpo`) |

Requires CUDA and `HF_TOKEN` if downloading adapters or dataset from HuggingFace.

## Weights & Biases

Experiment tracking defaults to **wandb** (project `aos-grpo`). Configure via [`apps/training/.env.example`](../training/.env.example):

```bash
cp apps/training/.env.example apps/training/.env
# Set WANDB_API_KEY in apps/training/.env (never commit)
```

Optional env vars: `WANDB_ENTITY`, `WANDB_PROJECT_GRPO`, `WANDB_RUN_NAME`. Disable with `--report-to none`.

## Run on Vertex AI

For GPU training on Google Cloud (Custom Jobs, GCS staging, Artifact Registry images), see [`apps/training/vertex/README.md`](../training/vertex/README.md).
