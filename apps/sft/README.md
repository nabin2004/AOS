# SFT — Qwen2.5-Coder Manim Trajectory Fine-Tuning

Fine-tunes **Qwen2.5-Coder-7B-Instruct** on Code Agent trajectories using LoRA + TRL `SFTTrainer`.

**Base model:** [`Qwen/Qwen2.5-Coder-7B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct) (dense 7.61B; QLoRA fits T4/Colab with `--kaggle`/`--colab`). See [docs/MODEL_SELECTION.md](docs/MODEL_SELECTION.md) for the FYP justification.

## Layout


| Module                     | Role                                                             |
| -------------------------- | ---------------------------------------------------------------- |
| `[config.py](config.py)`   | `TrainingConfig` dataclass, LoRA/SFTConfig factories, CLI parser |
| `[data.py](data.py)`       | Load JSONL from HF or local path, filter, normalize tool args    |
| `[model.py](model.py)`     | Tokenizer + CausalLM load, 4-bit quant (Gemma multimodal path kept for LEGACY) |
| `[trainer.py](trainer.py)` | Build `SFTTrainer`, train, save adapter + tokenizer              |
| `[run.py](run.py)`         | CLI entrypoint                                                   |
| `[infer.py](infer.py)`     | Load adapter; multi-turn tool loop (or `--no-tools` one-shot)    |
| `[infer_tools.py](infer_tools.py)` | Qwen/Gemma tool-call parse + CodeMode / Manim execution |
| `[preflight_sft.py](preflight_sft.py)` | Pre-flight chat template + mask checks before training |
| `[chat_template.py](chat_template.py)` | Training Jinja + `{% generation %}` markers for assistant-only loss |
| `[docs/MODEL_SELECTION.md](docs/MODEL_SELECTION.md)` | Why Qwen2.5-Coder-7B (report-ready) |
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
| `--model-id`      | Hugging Face model id (default: `Qwen/Qwen2.5-Coder-7B-Instruct`) |
| `--epochs`        | Training epochs                                          |
| `--batch-size`    | Per-device batch size                                    |
| `--learning-rate` | AdamW learning rate                                      |
| `--no-4bit`       | Full BF16 instead of 4-bit (more VRAM)                   |
| `--report-to`     | Logging backend (`wandb` default; use `none` to disable) |
| `--kaggle`        | T4-friendly preset (batch 1, seq 4096, packing off)      |
| `--colab`         | Colab preset: GPU-safe settings, output under Google Drive |
| `--runpod`        | RunPod preset: GPU-safe settings, output under `/workspace` |
| `--seq-len`       | Max sequence length (default 16384; 4096 with `--kaggle`) |
| `--packing` / `--no-packing` | Sequence packing (default **off** for long trajectories) |
| `--grad-accum`    | Gradient accumulation steps                              |
| `--device-map`    | Model device map (`auto` or GPU index like `0`)          |
| `--no-strip-towers` | Keep vision/audio towers loaded (Gemma LEGACY only)    |
| `--attn-implementation` | Attention backend: `sdpa` (default), `eager`, `flash_attention_2` |
| `--use-liger-kernel` | Enable liger-kernel fused ops (~2GB activation savings on T4) |
| `--push-to-hub` | Upload LoRA adapter to Hugging Face Hub after training |
| `--hub-model-id` | HF model repo id for adapter upload (default: `nabin2004/AOS-qwen25-coder-7b-manim-sft`) |
| `--run-name`      | W&B run name (default: `qwen25-coder-7b-manim-sft`, group `qwen25-coder-7b-manim`) |
| `--hub-private` | Create/upload the Hub model repo as private |


Edit defaults in `[config.py](config.py)` (`TrainingConfig`).

## Pre-flight (run before a long training job)

Qwen2.5-Coder needs correct ChatML + tool formatting and `{% generation %}` markers for `assistant_only_loss`. Run this before a long job:

```bash
cd apps/sft
uv run python preflight_sft.py --colab
uv run python preflight_sft.py --kaggle --load-model   # optional GPU smoke load
```

Checks: rendered template has `<|im_start|>assistant` and `<tool_call>` / `<tool_response>`, assistant loss masks are non-zero, tool errors are masked but visible in context.

Legacy mask test: `uv run python test_assistant_mask.py`.

## Inference after fine-tuning

Trajectory adapters are trained on **multi-turn Code Agent tool calls** (`run_code` → write/compile → final fenced Manim), not single-turn lecture prose. `infer.py` defaults to that same tool loop.

```bash
cd apps/sft
uv run python infer.py --adapter-dir ./qwen25-coder-7b-manim-ft \
  --prompt "Animate a unit circle morphing into an ellipse under a 2x2 matrix."
```

Colab (after training to `/content/qwen25-coder-7b-manim-ft`):

```bash
uv run --package sft python apps/sft/infer.py \
  --adapter-dir /content/qwen25-coder-7b-manim-ft \
  --colab \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

Colab (load adapter from Hugging Face Hub):

```bash
uv run --package sft python apps/sft/infer.py \
  --adapter-dir nabin2004/AOS-qwen25-coder-7b-manim-sft \
  --colab \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

Use a training-set prompt for a quick sanity check:

```bash
uv run python infer.py --adapter-dir ./qwen25-coder-7b-manim-ft --dataset-index 0
```

One-shot smoke check (no tools — often falls back to base-model lecture prose):

```bash
uv run python infer.py --adapter-dir ./qwen25-coder-7b-manim-ft --no-tools \
  --prompt "Animate a circle."
```

| Flag | Description |
|------|-------------|
| `--adapter-dir` | Output dir from training, or HF model repo id (default: `qwen25-coder-7b-manim-ft` or Colab Drive path with `--colab`) |
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

### CodeMode eval gate (GGUF / Ollama)

Hybrid/local coder uses compact `CODE_PROMPT_LOCAL` (Infer-style). Before calling a GGUF “ready”, run a greedy OpenAI-compat probe with that same prompt. Pass = first `run_code` nests Manim inside `manim_write` / `compile_manim_code` (no top-level `from manim import *`):

```bash
# Ollama serving AOS-qwen25-coder-7b-manim-gguf
uv run python diagnostics/codemode_eval_gate.py
# Optional: probe the long cloud CODE_PROMPT against the 31B GGUF
uv run python diagnostics/codemode_eval_gate.py --prompt-variant full
```

Filter star-import `run_code` rows out of a tool_trace JSONL (writes a sibling `*.codemode_clean.jsonl`):

```bash
uv run python filter_codemode.py ../agents/export_traces/coder_sft/tool_trace.train.jsonl
```

### Re-SFT on cleaned CodeMode data (next GPU session)

Durable fix after prompt workaround: train 31B on filtered tool_trace (no top-level `from manim import *` in `run_code`):

```bash
cd apps/sft
# Already generated locally (277 train / 27 val after filter):
#   ../agents/export_traces/coder_sft/tool_trace.train.codemode_clean.jsonl
#   ../agents/export_traces/coder_sft/tool_trace.val.codemode_clean.jsonl

uv run python run.py \
  --data-path ../agents/export_traces/coder_sft/tool_trace.train.codemode_clean.jsonl \
  --output-dir ./qwen25-coder-7b-manim-ft-codemode \
  --epochs 2 \
  --report-to none
```

Then merge → GGUF → re-run `diagnostics/codemode_eval_gate.py` (and `--prompt-variant full` once the weights learn the contract under the long cloud prompt).

## Merge adapter for deployment

Training saves **LoRA adapter weights only**. For vLLM or a merged Hugging Face upload, merge on **CPU in bf16** — never merge into the 4-bit training checkpoint:

```bash
cd apps/sft
uv run python merge_adapter.py \
  --adapter-dir ./qwen25-coder-7b-manim-ft \
  --output-dir ./qwen25-coder-7b-manim-merged
```

Push merged weights to Hugging Face (separate repo from the LoRA adapter):

```bash
export HF_TOKEN=hf_...   # write token; never commit
uv run python merge_adapter.py \
  --adapter-dir ./qwen25-coder-7b-manim-ft \
  --output-dir ./qwen25-coder-7b-manim-merged \
  --push-to-hub
```

**Default merged repo:** [nabin2004/AOS-qwen25-coder-7b-manim-merged](https://huggingface.co/nabin2004/AOS-qwen25-coder-7b-manim-merged)

| Flag | Description |
|------|-------------|
| `--push-to-hub` | Upload merged safetensors + tokenizer after merge |
| `--hub-repo-id` | HF model repo (default: `nabin2004/AOS-qwen25-coder-7b-manim-merged`) |
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
  --adapter-dir ./qwen25-coder-7b-manim-ft \
  --output-dir ./qwen25-coder-7b-manim-merged

# 2. Export GGUF + create Ollama model
export LLAMA_CPP_DIR=~/llama.cpp
uv run python export_gguf.py \
  --model-dir ./qwen25-coder-7b-manim-merged \
  --output-dir ./qwen25-coder-7b-manim-gguf

# 2b. Export GGUF + push to Hugging Face (separate repo from merged HF weights)
export HF_TOKEN=hf_...
uv run python export_gguf.py \
  --model-dir ./qwen25-coder-7b-manim-merged \
  --output-dir ./qwen25-coder-7b-manim-gguf \
  --push-to-hub

# 3. Run locally
ollama run aos-qwen25-coder-7b-manim
```

**Default GGUF repo:** [nabin2004/AOS-qwen25-coder-7b-manim-gguf](https://huggingface.co/nabin2004/AOS-qwen25-coder-7b-manim-gguf)

| Flag | Description |
|------|-------------|
| `--model-dir` | Merged HF directory from `merge_adapter.py` |
| `--output-dir` | Where GGUF files and `Modelfile` are written |
| `--model-name` | Ollama model tag (default: `aos-qwen25-coder-7b-manim`) |
| `--llama-cpp-dir` | llama.cpp clone path (default: `$LLAMA_CPP_DIR` or `./llama.cpp`) |
| `--quantize` | Quant type (default: `Q4_K_M`); use `none` for F16 only |
| `--skip-ollama-create` | Write files only; run `ollama create` yourself |
| `--push-to-hub` | Upload GGUF + Modelfile to Hugging Face after export |
| `--hub-repo-id` | HF model repo (default: `nabin2004/AOS-qwen25-coder-7b-manim-gguf`) |
| `--hub-private` | Create/upload as a private repo |
| `--hub-revision` | Optional branch or tag for the upload |
| `--upload-f16` | Include F16 intermediate in Hub upload (large; skipped by default) |

### Hub repos summary

| Artifact | Default repo | Upload command |
|----------|--------------|----------------|
| LoRA adapter | [nabin2004/AOS-qwen25-coder-7b-manim-sft](https://huggingface.co/nabin2004/AOS-qwen25-coder-7b-manim-sft) | `upload_adapter.py` or `run.py --push-to-hub` |
| Merged bf16 | [nabin2004/AOS-qwen25-coder-7b-manim-merged](https://huggingface.co/nabin2004/AOS-qwen25-coder-7b-manim-merged) | `merge_adapter.py --push-to-hub` |
| GGUF (Q4_K_M) | [nabin2004/AOS-qwen25-coder-7b-manim-gguf](https://huggingface.co/nabin2004/AOS-qwen25-coder-7b-manim-gguf) | `export_gguf.py --push-to-hub` |

Use the model through Ollama's OpenAI-compatible API at `http://localhost:11434/v1` — see
[`apps/server/README.md`](../server/README.md).

## Publish adapter to Hugging Face

Training saves **LoRA adapter weights only** (not merged). Publish to the Hub with a write token:

**Default model repo:** [nabin2004/AOS-qwen25-coder-7b-manim-sft](https://huggingface.co/nabin2004/AOS-qwen25-coder-7b-manim-sft)

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
uv run python upload_adapter.py --adapter-dir ./qwen25-coder-7b-manim-ft
uv run python upload_adapter.py --adapter-dir /content/qwen25-coder-7b-manim-ft --colab
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
!uv run --package sft python apps/sft/preflight_sft.py --colab
!uv run --package sft python apps/sft/run.py --colab --epochs 1 --report-to none
```

Train and push to Hugging Face in one step:

```bash
!uv run --package sft python apps/sft/run.py --colab --epochs 1 --report-to none --push-to-hub
```

Infer after training (local adapter):

```bash
!uv run --package sft python apps/sft/infer.py \
  --adapter-dir /content/qwen25-coder-7b-manim-ft \
  --colab \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

Or infer from the Hub (no local adapter copy):

```bash
!uv run --package sft python apps/sft/infer.py \
  --adapter-dir nabin2004/AOS-qwen25-coder-7b-manim-sft \
  --colab \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

| Environment | Flag | Default output dir |
|-------------|------|--------------------|
| **Colab** | `--colab` (auto when `COLAB_RELEASE_TAG` set) | `/content/drive/MyDrive/qwen25-coder-7b-manim-ft` |
| Kaggle | `--kaggle --output-dir /kaggle/working/...` | notebook output |
| RunPod | `--runpod` | `/workspace/qwen25-coder-7b-manim-ft` |
| Local | omit flags | `apps/sft/qwen25-coder-7b-manim-ft` |

Notes:

- `--colab` applies the same GPU-safe training settings as `--kaggle` (batch 1, seq 4096, packing off).
- If Drive is not mounted, output falls back to `/content/qwen25-coder-7b-manim-ft` (ephemeral — lost when runtime disconnects).
- Override output with `--output-dir /content/drive/MyDrive/my-run` or `export SFT_OUTPUT_DIR=...`.
- RunPod users: use `--runpod` instead (saves under `/workspace/qwen25-coder-7b-manim-ft`).

## Run on Kaggle (T4×2)

The `--kaggle` preset targets T4 GPUs and is suitable for **Qwen2.5-Coder-7B** QLoRA (seq 4096, packing off). Add a notebook secret `HF_TOKEN` for Hub downloads.

```bash
export UV_LINK_MODE=copy
export HF_TOKEN=...   # from Kaggle secrets
cd /kaggle/working && git clone https://github.com/<your-org>/AOS.git AOS && cd AOS

uv sync --package sft
uv run --package sft python apps/sft/run.py --kaggle \
  --report-to none \
  --output-dir /kaggle/working/qwen25-coder-7b-manim-ft
```

Notes:

- The `--kaggle` preset is also applied automatically when `KAGGLE_KERNEL_RUN_TYPE` is set.
- Dataset rows use structured `tool_calls` + `tool` messages (OpenAI-style); arguments are normalized to dicts; pre-exported `messages` JSONL is passed through after normalization.
- Default training template is [`templates/qwen25_coder_training.jinja`](templates/qwen25_coder_training.jinja) with `assistant_only_loss=True` so tool errors are visible but not trained on. Legacy Gemma Jinja remains for `--model-id` overrides.
- Run [`preflight_sft.py`](preflight_sft.py) before a long run (replaces manual template inspection).
- Default attention is **`sdpa`**. Packing defaults to **off** (long agent trajectories).
- Harmless log noise is expected: BitsAndBytes `FutureWarning`, `warmup_ratio` deprecation, wandb init delay.
- Adapter weights and tokenizer are written under `/kaggle/working/` (persist as notebook output).
- If you hit CUDA OOM, lower sequence length: `--seq-len 2048` (keep `--batch-size 1`).
- `UV_LINK_MODE=copy` avoids uv hardlink warnings on Kaggle's filesystem.
- Set `HF_TOKEN` as a Kaggle secret for faster Hub downloads.
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

Optional env vars: `WANDB_ENTITY`, `WANDB_PROJECT_SFT`, `WANDB_RUN_NAME`. Default run name: `qwen25-coder-7b-manim-sft` (group `qwen25-coder-7b-manim`, tags `qwen25-coder-7b,manim,aos,sft`). Disable with `--report-to none`.

## Run on Vertex AI

For GPU training on Google Cloud (Custom Jobs, GCS staging, Artifact Registry images), see `[apps/training/vertex/README.md](../training/vertex/README.md)`.

## Dependencies

Requires a recent **transformers** / **trl** / **peft** stack (`apps/sft/pyproject.toml`). 4-bit training requires `bitsandbytes` (CUDA). Install via workspace:

```bash
cd apps/sft && uv sync
```

Optional activation-memory savings on T4/L4 (~2GB):

```bash
uv sync --package sft --extra liger
uv run python run.py --colab --use-liger-kernel --report-to none
```

Model loading uses `AutoModelForImageTextToText` (falls back to `AutoModelForCausalLM` on older transformers).
