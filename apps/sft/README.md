# SFT — Gemma 4 Manim Trajectory Fine-Tuning

Fine-tunes Gemma 4 E2B/E4B on Code Agent trajectories using LoRA + TRL `SFTTrainer`.

## Layout


| Module                     | Role                                                             |
| -------------------------- | ---------------------------------------------------------------- |
| `[config.py](config.py)`   | `TrainingConfig` dataclass, LoRA/SFTConfig factories, CLI parser |
| `[data.py](data.py)`       | Load JSONL from HF or local path, filter, Gemma chat formatting  |
| `[model.py](model.py)`     | Tokenizer + model load, 4-bit quant, freeze multimodal towers    |
| `[trainer.py](trainer.py)` | Build `SFTTrainer`, train, save adapter + tokenizer              |
| `[run.py](run.py)`         | CLI entrypoint                                                   |
| `[upload_dataset.py](upload_dataset.py)` | Publish trajectories to Hugging Face Hub               |


## Dataset

**Default:** [nabin2004/AOS-Trajectories](https://huggingface.co/datasets/nabin2004/AOS-Trajectories) on Hugging Face (public).

| HF path | Use |
|---------|-----|
| `trajectories.jsonl` | Raw agent trajectories — **used by this trainer** |
| `tool_trace/train.jsonl` | OpenAI-style tool-calling format (export / external finetune) |
| `tool_trace/val.jsonl` | Held-out tool trace split |

Local override: `--data-path ../agents/training_data/trajectories.jsonl`

### Raw trajectory schema

One JSON object per line:

- `user_prompt` (or `prompt`) — user task
- `trajectory` — list of `{input, output}` tool-call steps
- `final_code` — successful Manim script (required)
- `summary` (or `narration`) — optional narration text
- `success` — records with `success: false` or missing `final_code` are skipped

## Usage

```bash
cd apps/sft
uv run python run.py
uv run python run.py --dataset-repo nabin2004/AOS-Trajectories
uv run python run.py --data-path ../agents/training_data/trajectories.jsonl
uv run python run.py --output-dir ./my-run --epochs 3 --batch-size 1
uv run python run.py --no-4bit --report-to none
```

### CLI flags


| Flag              | Description                                              |
| ----------------- | -------------------------------------------------------- |
| `--dataset-repo`  | HF dataset id (default: `nabin2004/AOS-Trajectories`)    |
| `--dataset-file`  | File within HF repo (default: `trajectories.jsonl`)      |
| `--data-path`     | Local trajectory JSONL override (skips Hub download)      |
| `--output-dir`    | Output directory for adapter + tokenizer                 |
| `--model-id`      | Hugging Face model id (default: `google/gemma-4-E2B-it`) |
| `--epochs`        | Training epochs                                          |
| `--batch-size`    | Per-device batch size                                    |
| `--learning-rate` | AdamW learning rate                                      |
| `--no-4bit`       | Full BF16 instead of 4-bit (needs ~80GB+ VRAM)           |
| `--report-to`     | Logging backend (`wandb` default; use `none` to disable) |
| `--kaggle`        | T4-friendly preset: batch 1, seq 2048, GPU 0, strip towers |
| `--seq-len`       | Max packed sequence length                               |
| `--grad-accum`    | Gradient accumulation steps                              |
| `--device-map`    | Model device map (`auto` or GPU index like `0`)          |
| `--no-strip-towers` | Keep vision/audio towers loaded (more VRAM)            |


Edit defaults in `[config.py](config.py)` (`TrainingConfig`).

## Run on Kaggle (T4×2)

Use a Kaggle notebook with **GPU T4 x2** enabled. Add a notebook secret `HF_TOKEN` with a Hugging Face token that has accepted the [google/gemma-4-E2B-it](https://huggingface.co/google/gemma-4-E2B-it) license.

```bash
export UV_LINK_MODE=copy
export HF_TOKEN=...   # from Kaggle secrets
cd /kaggle/working && git clone https://github.com/<your-org>/AOS.git AOS && cd AOS

uv sync --package sft
uv run --package sft python apps/sft/run.py --kaggle \
  --report-to none \
  --output-dir /kaggle/working/gemma4-manim-ft
```

Notes:

- The `--kaggle` preset is also applied automatically when `KAGGLE_KERNEL_RUN_TYPE` is set.
- Dataset rows are emitted as a `messages` column for TRL conversational SFT.
- Gemma 4 has no TRL training chat template yet; `assistant_only_loss` is auto-disabled and the full sequence is trained.
- The Kaggle preset disables sequence packing (T4 uses SDPA, not Flash Attention).
- Adapter weights and tokenizer are written under `/kaggle/working/` (persist as notebook output).
- If you hit CUDA OOM, lower sequence length: `--seq-len 1024` (keep `--batch-size 1`).
- `UV_LINK_MODE=copy` avoids uv hardlink warnings on Kaggle's filesystem.
- Set `HF_TOKEN` as a Kaggle secret for faster Hub downloads and gated model access.
- Optional: add a `WANDB_API_KEY` secret to re-enable wandb logging with `--kaggle`.

## Publish / refresh dataset on Hugging Face

After collecting traces and running `export_local_sft.py` in `apps/agents`:

```bash
export HF_TOKEN=hf_...   # write token; never commit
cd apps/sft
uv sync
uv run python upload_dataset.py
```

Uploads `trajectories.jsonl`, `tool_trace/train.jsonl`, `tool_trace/val.jsonl`, and `metadata.jsonl` to the Hub.

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
