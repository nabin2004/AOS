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
| `[infer.py](infer.py)`     | Load adapter; multi-turn tool loop (or `--no-tools` one-shot)    |
| `[infer_tools.py](infer_tools.py)` | Gemma tool-call parse + CodeMode / Manim tool execution   |
| `[preflight_gemma4.py](preflight_gemma4.py)` | Pre-flight chat template + mask checks before training |
| `[merge_adapter.py](merge_adapter.py)` | Merge LoRA into bf16 base for vLLM / HF deploy (CPU)     |
| `[export_gguf.py](export_gguf.py)` | Convert merged HF weights to GGUF for Ollama (via llama.cpp) |
| `[upload_dataset.py](upload_dataset.py)` | Publish trajectories to Hugging Face Hub               |
| `[upload_adapter.py](upload_adapter.py)` | Publish LoRA adapter to Hugging Face Hub               |


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
| `--push-to-hub` | Upload LoRA adapter to Hugging Face Hub after training |
| `--hub-model-id` | HF model repo id for adapter upload (default: `nabin2004/AOS-gemma4-manim-sft`) |
| `--hub-private` | Create/upload the Hub model repo as private |


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

Trajectory adapters are trained on **multi-turn Code Agent tool calls** (`run_code` → write/compile → final fenced Manim), not single-turn lecture prose. `infer.py` defaults to that same tool loop.

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

Colab (load adapter from Hugging Face Hub):

```bash
uv run --package sft python apps/sft/infer.py \
  --adapter-dir nabin2004/AOS-gemma4-manim-sft \
  --colab \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

Use a training-set prompt for a quick sanity check:

```bash
uv run python infer.py --adapter-dir ./gemma4-manim-ft --dataset-index 0
```

One-shot smoke check (no tools — often falls back to base-model lecture prose):

```bash
uv run python infer.py --adapter-dir ./gemma4-manim-ft --no-tools \
  --prompt "Animate a circle."
```

| Flag | Description |
|------|-------------|
| `--adapter-dir` | Output dir from training, or HF model repo id (default: `gemma4-manim-ft` or Colab Drive path with `--colab`) |
| `--prompt` | User task text |
| `--prompt-file` | Read prompt from a file |
| `--dataset-index` | Pull `user_prompt` from the HF trajectories dataset |
| `--max-new-tokens` | Generation limit (default: 2048) |
| `--temperature` | Sampling temperature; `0` = greedy (default: 0) |
| `--max-tool-rounds` | Max assistant tool-calling rounds (default: 8) |
| `--all-tools` | Also expose direct `manim_write` / `compile_manim_code` / `manim_read` (default: `run_code` only, matching SFT) |
| `--no-system-prompt` | Skip Code Agent system instructions prepended at infer time |
| `--output-dir` | Workspace for `manim_write` / `compile_manim_code` (default: `apps/agents/workspace/infer_runs/<timestamp>`) |
| `--no-tools` | Disable tool defs + loop; one-shot `generate` only |
| `--colab` / `--kaggle` / `--runpod` | Same VRAM-friendly load defaults as training |

With tools enabled, the script prepends a short Code Agent system prompt, exposes **`run_code` only** by default (matching training), retries empty assistant turns after tool errors, and exits with code **2** if no scene `.py` was written (hallucinated success). Use `--all-tools` only if you intentionally trained on direct tool calls.

Inference validates that the adapter directory saved a training chat template with `{% generation %}` markers (required for models trained with `assistant_only_loss=True`).

## Merge adapter for deployment

Training saves **LoRA adapter weights only**. For vLLM or a merged Hugging Face upload, merge on **CPU in bf16** — never merge into the 4-bit training checkpoint:

```bash
cd apps/sft
uv run python merge_adapter.py \
  --adapter-dir ./gemma4-manim-ft \
  --output-dir ./gemma4-manim-merged
```

Push merged weights to Hugging Face (separate repo from the LoRA adapter):

```bash
export HF_TOKEN=hf_...   # write token; never commit
uv run python merge_adapter.py \
  --adapter-dir ./gemma4-manim-ft \
  --output-dir ./gemma4-manim-merged \
  --push-to-hub
```

**Default merged repo:** [nabin2004/AOS-gemma4-manim-merged](https://huggingface.co/nabin2004/AOS-gemma4-manim-merged)

| Flag | Description |
|------|-------------|
| `--push-to-hub` | Upload merged safetensors + tokenizer after merge |
| `--hub-repo-id` | HF model repo (default: `nabin2004/AOS-gemma4-manim-merged`) |
| `--hub-private` | Create/upload as a private repo |
| `--hub-revision` | Optional branch or tag for the upload |

### Export to GGUF for Ollama

Convert the merged checkpoint to Q4_K_M GGUF and register it with Ollama. Requires a
recent [llama.cpp](https://github.com/ggml-org/llama.cpp) build (Gemma 4 support) and
Ollama 0.30+.

**Prerequisites:**

```bash
git clone https://github.com/ggml-org/llama.cpp
cd llama.cpp && cmake -B build && cmake --build build -j
# Ollama 0.30+ installed
```

**End-to-end:**

```bash
cd apps/sft

# 1. Merge (if not done already)
uv run python merge_adapter.py \
  --adapter-dir ./gemma4-manim-ft \
  --output-dir ./gemma4-manim-merged

# 2. Export GGUF + create Ollama model
export LLAMA_CPP_DIR=~/llama.cpp
uv run python export_gguf.py \
  --model-dir ./gemma4-manim-merged \
  --output-dir ./gemma4-manim-gguf

# 2b. Export GGUF + push to Hugging Face (separate repo from merged HF weights)
export HF_TOKEN=hf_...
uv run python export_gguf.py \
  --model-dir ./gemma4-manim-merged \
  --output-dir ./gemma4-manim-gguf \
  --push-to-hub

# 3. Run locally
ollama run aos-gemma4-manim
```

**Default GGUF repo:** [nabin2004/AOS-gemma4-manim-gguf](https://huggingface.co/nabin2004/AOS-gemma4-manim-gguf)

| Flag | Description |
|------|-------------|
| `--model-dir` | Merged HF directory from `merge_adapter.py` |
| `--output-dir` | Where GGUF files and `Modelfile` are written |
| `--model-name` | Ollama model tag (default: `aos-gemma4-manim`) |
| `--llama-cpp-dir` | llama.cpp clone path (default: `$LLAMA_CPP_DIR` or `./llama.cpp`) |
| `--quantize` | Quant type (default: `Q4_K_M`); use `none` for F16 only |
| `--skip-ollama-create` | Write files only; run `ollama create` yourself |
| `--push-to-hub` | Upload GGUF + Modelfile to Hugging Face after export |
| `--hub-repo-id` | HF model repo (default: `nabin2004/AOS-gemma4-manim-gguf`) |
| `--hub-private` | Create/upload as a private repo |
| `--hub-revision` | Optional branch or tag for the upload |
| `--upload-f16` | Include F16 intermediate in Hub upload (large; skipped by default) |

### Hub repos summary

| Artifact | Default repo | Upload command |
|----------|--------------|----------------|
| LoRA adapter | [nabin2004/AOS-gemma4-manim-sft](https://huggingface.co/nabin2004/AOS-gemma4-manim-sft) | `upload_adapter.py` or `run.py --push-to-hub` |
| Merged bf16 | [nabin2004/AOS-gemma4-manim-merged](https://huggingface.co/nabin2004/AOS-gemma4-manim-merged) | `merge_adapter.py --push-to-hub` |
| GGUF (Q4_K_M) | [nabin2004/AOS-gemma4-manim-gguf](https://huggingface.co/nabin2004/AOS-gemma4-manim-gguf) | `export_gguf.py --push-to-hub` |

Use the model through Ollama's OpenAI-compatible API at `http://localhost:11434/v1` — see
[`apps/server/README.md`](../server/README.md).

## Publish adapter to Hugging Face

Training saves **LoRA adapter weights only** (not merged). Publish to the Hub with a write token:

**Default model repo:** [nabin2004/AOS-gemma4-manim-sft](https://huggingface.co/nabin2004/AOS-gemma4-manim-sft)

### Push after training

```bash
export HF_TOKEN=hf_...   # write token; never commit
cd apps/sft
uv run python run.py --colab --epochs 1 --report-to none --push-to-hub
```

Optional flags: `--hub-model-id`, `--hub-private`.

### Push an existing adapter

```bash
export HF_TOKEN=hf_...
cd apps/sft
uv run python upload_adapter.py --adapter-dir ./gemma4-manim-ft
uv run python upload_adapter.py --adapter-dir /content/gemma4-manim-ft --colab
```

Uploads adapter weights, tokenizer, and `model_card.md` as the repo README. Skips `checkpoint-*` and other training artifacts.

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

Train and push to Hugging Face in one step:

```bash
!uv run --package sft python apps/sft/run.py --colab --epochs 1 --report-to none --push-to-hub
```

Infer after training (local adapter):

```bash
!uv run --package sft python apps/sft/infer.py \
  --adapter-dir /content/gemma4-manim-ft \
  --colab \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

Or infer from the Hub (no local adapter copy):

```bash
!uv run --package sft python apps/sft/infer.py \
  --adapter-dir nabin2004/AOS-gemma4-manim-sft \
  --colab \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
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
