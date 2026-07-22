# SFT — Gemma 4 Manim Trajectory Fine-Tuning

Fine-tunes Gemma 4 E2B/E4B on Code Agent trajectories using LoRA + TRL `SFTTrainer`.

## Layout


| Module                     | Role                                                             |
| -------------------------- | ---------------------------------------------------------------- |
| `[config.py](config.py)`   | `TrainingConfig` dataclass, LoRA/SFTConfig factories, CLI parser |
| `[data.py](data.py)`       | Load JSONL, filter successful runs, Gemma chat formatting        |
| `[model.py](model.py)`     | Tokenizer + model load, 4-bit quant, freeze multimodal towers    |
| `[trainer.py](trainer.py)` | Build `SFTTrainer`, train, save adapter + tokenizer              |
| `[run.py](run.py)`         | CLI entrypoint                                                   |


## Data format

Input JSONL records (one per trajectory). Keys from `[apps/agents/training_data/trajectories.jsonl](../agents/training_data/trajectories.jsonl)`:

- `user_prompt` (or `prompt`) — user task
- `trajectory` — list of `{input, output}` tool-call steps
- `final_code` — successful Manim script (required)
- `summary` (or `narration`) — optional narration text
- `success` — records with `success: false` or missing `final_code` are skipped

## Usage

```bash
cd apps/sft
uv run python run.py
uv run python run.py --data-path ../agents/training_data/trajectories.jsonl
uv run python run.py --output-dir ./my-run --epochs 3 --batch-size 1
uv run python run.py --no-4bit --report-to none
```

### CLI flags


| Flag              | Description                                              |
| ----------------- | -------------------------------------------------------- |
| `--data-path`     | Trajectory JSONL path                                    |
| `--output-dir`    | Output directory for adapter + tokenizer                 |
| `--model-id`      | Hugging Face model id (default: `google/gemma-4-E2B-it`) |
| `--epochs`        | Training epochs                                          |
| `--batch-size`    | Per-device batch size                                    |
| `--learning-rate` | AdamW learning rate                                      |
| `--no-4bit`       | Full BF16 instead of 4-bit (needs ~80GB+ VRAM)           |
| `--report-to`     | Logging backend (`wandb` default; use `none` to disable) |


Edit defaults in `[config.py](config.py)` (`TrainingConfig`).

## Weights & Biases

Experiment tracking defaults to **wandb** (project `aos-sft`). Configure via `[apps/training/.env.example](../training/.env.example)`:

```bash
cp apps/training/.env.example apps/training/.env
# Set WANDB_API_KEY in apps/training/.env (never commit)
```

Optional env vars: `WANDB_ENTITY`, `WANDB_PROJECT_SFT`, `WANDB_RUN_NAME`. Disable with `--report-to none`.

## Run on Vertex AI

For GPU training on Google Cloud (Custom Jobs, GCS staging, Artifact Registry images), see `[apps/training/vertex/README.md](../training/vertex/README.md)`.

## Dependencies

4-bit training requires `bitsandbytes` (CUDA). Install via workspace:

```bash
cd apps/sft && uv sync
```
