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
| `[infer.py](infer.py)`     | Load a fine-tuned adapter and generate a Manim response          |
| `[preflight_gemma4.py](preflight_gemma4.py)` | Pre-flight chat template + mask checks before training |
| `[merge_adapter.py](merge_adapter.py)` | Merge LoRA into bf16 base for vLLM / HF deploy (CPU)     |
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
| `--colab`         | Colab preset: GPU-safe settings, output under Google Drive |
| `--runpod`        | RunPod preset: GPU-safe settings, output under `/workspace` |
| `--seq-len`       | Max packed sequence length                               |
| `--grad-accum`    | Gradient accumulation steps                              |
| `--device-map`    | Model device map (`auto` or GPU index like `0`)          |
| `--no-strip-towers` | Keep vision/audio towers loaded (more VRAM)            |
| `--attn-implementation` | Attention backend: `eager` (default), `sdpa`, `flash_attention_2` |
| `--use-liger-kernel` | Enable liger-kernel fused ops (~2GB activation savings on T4) |


Edit defaults in `[config.py](config.py)` (`TrainingConfig`).

## Pre-flight (run before a long training job)

Gemma 4 unified models need correct chat-template formatting and `{% generation %}` markers for `assistant_only_loss`. Run this on Colab/Kaggle before `--epochs 2`:

```bash
cd apps/sft
uv run python preflight_gemma4.py --colab
uv run python preflight_gemma4.py --kaggle --load-model   # optional GPU smoke load
```

Checks: rendered template has `<|turn>model` (not `<unknown_role>`), assistant loss masks are non-zero, tool errors are masked but visible in context.

Legacy mask test: `uv run python test_assistant_mask.py`.

## Inference after fine-tuning

Load the LoRA adapter saved by `run.py` and generate a Manim response:

```bash
cd apps/sft
uv run python infer.py --adapter-dir ./gemma4-manim-ft \
  --prompt "Animate a unit circle morphing into an ellipse under a 2x2 matrix."
```

Colab (after training to `/content/gemma4-manim-ft`):

```bash
uv run --package sft python apps/sft/infer.py \
  --adapter-dir /content/gemma4-manim-ft \
  --colab \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

Use a training-set prompt for a quick sanity check:

```bash
uv run python infer.py --adapter-dir ./gemma4-manim-ft --dataset-index 0
```

| Flag | Description |
|------|-------------|
| `--adapter-dir` | Output dir from training (default: `gemma4-manim-ft` or Colab Drive path with `--colab`) |
| `--prompt` | User task text |
| `--prompt-file` | Read prompt from a file |
| `--dataset-index` | Pull `user_prompt` from the HF trajectories dataset |
| `--max-new-tokens` | Generation limit (default: 2048) |
| `--temperature` | Sampling temperature; `0` = greedy (default: 0.7) |
| `--colab` / `--kaggle` / `--runpod` | Same VRAM-friendly load defaults as training |

The script prints the raw assistant turn (tool calls and/or Python code). Render the extracted Manim script with your usual Code Agent or `manim` workflow to verify quality.

Inference validates that the adapter directory saved a training chat template with `{% generation %}` markers (required for models trained with `assistant_only_loss=True`).

## Merge adapter for deployment

Training saves **LoRA adapter weights only**. For vLLM or a merged Hugging Face upload, merge on **CPU in bf16** — never merge into the 4-bit training checkpoint:

```bash
cd apps/sft
uv run python merge_adapter.py \
  --adapter-dir ./gemma4-manim-ft \
  --output-dir ./gemma4-manim-merged
```

Quantize the merged model separately (GGUF / AWQ) if needed.

## Run on Google Colab

Mount Google Drive **before** training so adapter weights persist after the runtime disconnects. Do **not** use Kaggle `/kaggle/working/...` paths on Colab.

```python
# Cell 1 — mount Drive first (required for persistence)
from google.colab import drive
drive.mount("/content/drive")

import os
os.environ["HF_TOKEN"] = "..."  # Colab secret
```

```bash
# Cell 2 — clone + train
!git clone https://github.com/<your-org>/AOS.git /content/AOS
%cd /content/AOS
!pip install uv
!uv sync --package sft
!uv run --package sft python apps/sft/preflight_gemma4.py --colab
!uv run --package sft python apps/sft/run.py --colab --epochs 1 --report-to none
```

| Environment | Flag | Default output dir |
|-------------|------|--------------------|
| **Colab** | `--colab` (auto when `COLAB_RELEASE_TAG` set) | `/content/drive/MyDrive/gemma4-manim-ft` |
| Kaggle | `--kaggle --output-dir /kaggle/working/...` | notebook output |
| RunPod | `--runpod` | `/workspace/gemma4-manim-ft` |
| Local | omit flags | `apps/sft/gemma4-manim-ft` |

Notes:

- `--colab` applies the same GPU-safe training settings as `--kaggle` (batch 1, seq 2048, no packing).
- If Drive is not mounted, output falls back to `/content/gemma4-manim-ft` (ephemeral — lost when runtime disconnects).
- Override output with `--output-dir /content/drive/MyDrive/my-run` or `export SFT_OUTPUT_DIR=...`.
- RunPod users: use `--runpod` instead (saves under `/workspace/gemma4-manim-ft`).

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
- Dataset rows use structured `tool_calls` + `tool` messages (Gemma 4 native format); pre-exported `messages` JSONL is passed through unchanged.
- Gemma 4 uses [`templates/gemma4_training.jinja`](templates/gemma4_training.jinja) with `assistant_only_loss=True` so tool errors are visible but not trained on.
- Run [`preflight_gemma4.py`](preflight_gemma4.py) before a long run (replaces manual template inspection).
- Default attention is **`eager`** (Gemma 4 unified arch). Use `--attn-implementation sdpa` only after a successful preflight if you need the speed/VRAM tradeoff.
- Harmless log noise is expected: BitsAndBytes `FutureWarning`, `warmup_ratio` deprecation, wandb init delay.
- The Kaggle preset disables sequence packing and strips unused vision/audio towers.
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

Gemma 4 requires a recent **transformers** build with `gemma4_unified` support (`>=4.51.0` in `pyproject.toml`). If model load fails on Colab/Kaggle with an unknown architecture error:

```bash
pip install "git+https://github.com/huggingface/transformers.git"
```

4-bit training requires `bitsandbytes` (CUDA). Install via workspace:

```bash
cd apps/sft && uv sync
```

Optional activation-memory savings on T4/L4 (~2GB):

```bash
uv sync --package sft --extra liger
uv run python run.py --colab --use-liger-kernel --report-to none
```

Model loading uses `AutoModelForImageTextToText` (falls back to `AutoModelForCausalLM` on older transformers).
