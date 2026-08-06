# SFT — Gemma 4 Manim Instruction Fine-Tuning

Fine-tunes **Gemma 4 31B IT** on Manim instruction chat pairs using LoRA + TRL `SFTTrainer`.

**Base model:** [`google/gemma-4-31B-it`](https://huggingface.co/google/gemma-4-31B-it) (~80 GB VRAM for 4-bit LoRA at seq 8192). Kaggle T4 presets are not suitable for full 31B training.

## Layout


| Module                     | Role                                                             |
| -------------------------- | ---------------------------------------------------------------- |
| `[config.py](config.py)`   | `TrainingConfig` dataclass, LoRA/SFTConfig factories, CLI parser |
| `[data.py](data.py)`       | Load JSONL from HF or local path, filter, Gemma chat formatting  |
| `[model.py](model.py)`     | Tokenizer + model load, 4-bit quant, freeze multimodal towers    |
| `[trainer.py](trainer.py)` | Build `SFTTrainer`, train, save adapter + tokenizer              |
| `[run.py](run.py)`         | CLI entrypoint                                                   |
| `[train.sh](train.sh)`     | RunPod end-to-end: train → merge → GGUF → Hub pushes             |
| `[runpod_sft.ipynb](runpod_sft.ipynb)` | Minimal RunPod notebook (calls `train.sh`)                |
| `[infer.py](infer.py)`     | Load adapter; multi-turn tool loop (or `--no-tools` one-shot)    |
| `[infer_tools.py](infer_tools.py)` | Gemma tool-call parse + CodeMode / Manim tool execution   |
| `[preflight_gemma4.py](preflight_gemma4.py)` | Pre-flight chat template + mask checks before training |
| `[merge_adapter.py](merge_adapter.py)` | Merge LoRA into bf16 base for vLLM / HF deploy (CPU)     |
| `[export_gguf.py](export_gguf.py)` | Convert merged HF weights to GGUF for Ollama (via llama.cpp) |
| `[upload_dataset.py](upload_dataset.py)` | Publish trajectories to Hugging Face Hub               |
| `[upload_adapter.py](upload_adapter.py)` | Publish LoRA adapter to Hugging Face Hub               |


## Dataset

**Default:** [nabin2004/manim-sft](https://huggingface.co/datasets/nabin2004/manim-sft) on Hugging Face (38,491 rows).

| HF path | Use |
|---------|-----|
| `data/train.jsonl` | Manim instruction chat pairs — **used by this trainer** |

Each row has pre-built `messages` (system → user → assistant). The assistant turn is full Manim Python source. No tool calls.

**Legacy agent trajectories:** [nabin2004/AOS-Trajectories](https://huggingface.co/datasets/nabin2004/AOS-Trajectories) (`trajectories.jsonl`, `tool_trace/*.jsonl`) — use `--dataset-repo nabin2004/AOS-Trajectories --dataset-file trajectories.jsonl` or `--data-path`.

Local override: `--data-path /path/to/train.jsonl`

### manim-sft schema

One JSON object per line:

- `messages` — list of `{role, content}` turns (system, user, assistant)
- `metadata` — optional provenance (`source`, `quality_tier`, etc.)

Legacy trajectory rows (`user_prompt`, `trajectory`, `final_code`) are still supported when using `--data-path` or AOS-Trajectories.

## Usage

```bash
cd apps/sft
uv run python run.py
uv run python run.py --dataset-repo nabin2004/manim-sft --dataset-file data/train.jsonl
uv run python run.py --data-path ../agents/training_data/trajectories.jsonl
uv run python run.py --output-dir ./my-run --epochs 1 --batch-size 1
uv run python run.py --no-4bit --report-to none
```

Post-training inference for manim-sft models uses direct codegen (not the Code Agent tool loop):

```bash
uv run python infer.py --adapter-dir ./gemma4-31b-manim-ft --no-tools --prompt "Animate a circle."
uv run python infer.py --adapter-dir ./gemma4-31b-manim-ft --dataset-index 0 --no-tools
```

### CLI flags


| Flag              | Description                                              |
| ----------------- | -------------------------------------------------------- |
| `--dataset-repo`  | HF dataset id (default: `nabin2004/manim-sft`)    |
| `--dataset-file`  | File within HF repo (default: `data/train.jsonl`)      |
| `--data-path`     | Local trajectory JSONL override (skips Hub download)      |
| `--output-dir`    | Output directory for adapter + tokenizer                 |
| `--model-id`      | Hugging Face model id (default: `google/gemma-4-31B-it`) |
| `--epochs`        | Training epochs                                          |
| `--batch-size`    | Per-device batch size                                    |
| `--learning-rate` | AdamW learning rate                                      |
| `--no-4bit`       | Full BF16 instead of 4-bit (needs ~80GB+ VRAM)           |
| `--report-to`     | Logging backend (`wandb` default; use `none` to disable) |
| `--kaggle`        | T4-friendly preset (not recommended for 31B; warns at startup) |
| `--colab`         | Colab preset: T4-safe settings (seq 2048), output under Google Drive |
| `--runpod`        | RunPod A100 preset: full seq 8192, output under `/workspace` |
| `--seq-len`       | Max packed sequence length                               |
| `--grad-accum`    | Gradient accumulation steps                              |
| `--device-map`    | Model device map (`auto` or GPU index like `0`)          |
| `--no-strip-towers` | Keep vision/audio towers loaded (more VRAM)            |
| `--attn-implementation` | Attention backend: `eager` (default), `sdpa`, `flash_attention_2` |
| `--use-liger-kernel` | Enable liger-kernel fused ops (~2GB activation savings on T4) |
| `--push-to-hub` | Upload LoRA adapter to Hugging Face Hub after training |
| `--hub-model-id` | HF model repo id for adapter upload (default: `nabin2004/AOS-gemma4-31b-manim-sft`) |
| `--run-name`      | W&B run name (default: `gemma4-31b-manim-sft`, group `gemma4-31b-manim`) |
| `--hub-private` | Create/upload the Hub model repo as private |


Edit defaults in `[config.py](config.py)` (`TrainingConfig`).

## Pre-flight (run before a long training job)

Gemma 4 unified models need correct chat-template formatting and `{% generation %}` markers for `assistant_only_loss`. Run this on RunPod/Colab/Kaggle before a long job:

```bash
cd apps/sft
uv run python preflight_gemma4.py --runpod
uv run python preflight_gemma4.py --colab
uv run python preflight_gemma4.py --kaggle --load-model   # optional GPU smoke load
```

Checks: rendered template has `<|turn>model` (not `<unknown_role>`), assistant loss masks are non-zero, tool errors are masked but visible in context.

Legacy mask test: `uv run python test_assistant_mask.py`.

## Inference after fine-tuning

Trajectory adapters are trained on **multi-turn Code Agent tool calls** (`run_code` → write/compile → final fenced Manim), not single-turn lecture prose. `infer.py` defaults to that same tool loop.

```bash
cd apps/sft
uv run python infer.py --adapter-dir ./gemma4-31b-manim-ft \
  --prompt "Animate a unit circle morphing into an ellipse under a 2x2 matrix."
```

Colab (after training to `/content/gemma4-31b-manim-ft`):

```bash
uv run --package sft python apps/sft/infer.py \
  --adapter-dir /content/gemma4-31b-manim-ft \
  --colab \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

Colab (load adapter from Hugging Face Hub):

```bash
uv run --package sft python apps/sft/infer.py \
  --adapter-dir nabin2004/AOS-gemma4-31b-manim-sft \
  --colab \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

Use a training-set prompt for a quick sanity check:

```bash
uv run python infer.py --adapter-dir ./gemma4-31b-manim-ft --dataset-index 0
```

One-shot smoke check (no tools — often falls back to base-model lecture prose):

```bash
uv run python infer.py --adapter-dir ./gemma4-31b-manim-ft --no-tools \
  --prompt "Animate a circle."
```

| Flag | Description |
|------|-------------|
| `--adapter-dir` | Output dir from training, or HF model repo id (default: `gemma4-31b-manim-ft` or Colab Drive path with `--colab`) |
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
| `--colab` / `--kaggle` / `--runpod` | Same load defaults as the matching training preset |

With tools enabled, the script prepends a short Code Agent system prompt, exposes **`run_code` only** by default (matching training), retries empty assistant turns after tool errors, and exits with code **2** if no scene `.py` was written (hallucinated success). Use `--all-tools` only if you intentionally trained on direct tool calls.

Inference validates that the adapter directory saved a training chat template with `{% generation %}` markers (required for models trained with `assistant_only_loss=True`).

### CodeMode eval gate (GGUF / Ollama)

Hybrid/local coder uses compact `CODE_PROMPT_LOCAL` (Infer-style). Before calling a GGUF “ready”, run a greedy OpenAI-compat probe with that same prompt. Pass = first `run_code` nests Manim inside `manim_write` / `compile_manim_code` (no top-level `from manim import *`):

```bash
# Ollama serving AOS-gemma4-31b-manim-gguf
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
  --output-dir ./gemma4-31b-manim-ft-codemode \
  --epochs 2 \
  --report-to none
```

Then merge → GGUF → re-run `diagnostics/codemode_eval_gate.py` (and `--prompt-variant full` once the weights learn the contract under the long cloud prompt).

## Merge adapter for deployment

Training saves **LoRA adapter weights only**. For vLLM or a merged Hugging Face upload, merge on **CPU in bf16** — never merge into the 4-bit training checkpoint:

```bash
cd apps/sft
uv run python merge_adapter.py \
  --adapter-dir ./gemma4-31b-manim-ft \
  --output-dir ./gemma4-31b-manim-merged
```

Push merged weights to Hugging Face (separate repo from the LoRA adapter):

```bash
export HF_TOKEN=hf_...   # write token; never commit
uv run python merge_adapter.py \
  --adapter-dir ./gemma4-31b-manim-ft \
  --output-dir ./gemma4-31b-manim-merged \
  --push-to-hub
```

**Default merged repo:** [nabin2004/AOS-gemma4-31b-manim-merged](https://huggingface.co/nabin2004/AOS-gemma4-31b-manim-merged)

| Flag | Description |
|------|-------------|
| `--push-to-hub` | Upload merged safetensors + tokenizer after merge |
| `--hub-repo-id` | HF model repo (default: `nabin2004/AOS-gemma4-31b-manim-merged`) |
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
  --adapter-dir ./gemma4-31b-manim-ft \
  --output-dir ./gemma4-31b-manim-merged

# 2. Export GGUF + create Ollama model
export LLAMA_CPP_DIR=~/llama.cpp
uv run python export_gguf.py \
  --model-dir ./gemma4-31b-manim-merged \
  --output-dir ./gemma4-31b-manim-gguf

# 2b. Export GGUF + push to Hugging Face (separate repo from merged HF weights)
export HF_TOKEN=hf_...
uv run python export_gguf.py \
  --model-dir ./gemma4-31b-manim-merged \
  --output-dir ./gemma4-31b-manim-gguf \
  --push-to-hub

# 3. Run locally
ollama run aos-gemma4-31b-manim
```

**Default GGUF repo:** [nabin2004/AOS-gemma4-31b-manim-gguf](https://huggingface.co/nabin2004/AOS-gemma4-31b-manim-gguf)

| Flag | Description |
|------|-------------|
| `--model-dir` | Merged HF directory from `merge_adapter.py` |
| `--output-dir` | Where GGUF files and `Modelfile` are written |
| `--model-name` | Ollama model tag (default: `aos-gemma4-31b-manim`) |
| `--llama-cpp-dir` | llama.cpp clone path (default: `$LLAMA_CPP_DIR` or `./llama.cpp`) |
| `--quantize` | Quant type (default: `Q4_K_M`); use `none` for F16 only |
| `--skip-ollama-create` | Write files only; run `ollama create` yourself |
| `--push-to-hub` | Upload GGUF + Modelfile to Hugging Face after export |
| `--hub-repo-id` | HF model repo (default: `nabin2004/AOS-gemma4-31b-manim-gguf`) |
| `--hub-private` | Create/upload as a private repo |
| `--hub-revision` | Optional branch or tag for the upload |
| `--upload-f16` | Include F16 intermediate in Hub upload (large; skipped by default) |

### Hub repos summary

| Artifact | Default repo | Upload command |
|----------|--------------|----------------|
| LoRA adapter | [nabin2004/AOS-gemma4-31b-manim-sft](https://huggingface.co/nabin2004/AOS-gemma4-31b-manim-sft) | `upload_adapter.py` or `run.py --push-to-hub` |
| Merged bf16 | [nabin2004/AOS-gemma4-31b-manim-merged](https://huggingface.co/nabin2004/AOS-gemma4-31b-manim-merged) | `merge_adapter.py --push-to-hub` |
| GGUF (Q4_K_M) | [nabin2004/AOS-gemma4-31b-manim-gguf](https://huggingface.co/nabin2004/AOS-gemma4-31b-manim-gguf) | `export_gguf.py --push-to-hub` |

Use the model through Ollama's OpenAI-compatible API at `http://localhost:11434/v1` — see
[`apps/server/README.md`](../server/README.md).

## Publish adapter to Hugging Face

Training saves **LoRA adapter weights only** (not merged). Publish to the Hub with a write token:

**Default model repo:** [nabin2004/AOS-gemma4-31b-manim-sft](https://huggingface.co/nabin2004/AOS-gemma4-31b-manim-sft)

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
uv run python upload_adapter.py --adapter-dir ./gemma4-31b-manim-ft
uv run python upload_adapter.py --adapter-dir /content/gemma4-31b-manim-ft --colab
```

Uploads adapter weights, tokenizer, and `model_card.md` as the repo README. Skips `checkpoint-*` and other training artifacts.

## Run on RunPod (recommended for full 31B)

Prefer RunPod **A100 80GB** over Colab for Gemma 4 31B (`seq_len=8192` 4-bit LoRA needs ~80 GB VRAM).

Use the minimal notebook [`runpod_sft.ipynb`](runpod_sft.ipynb), or run [`train.sh`](train.sh) directly. Both run the full pipeline:

**preflight → SFT + push LoRA → merge + push → llama.cpp → GGUF + push**

1. Deploy a GPU Pod with a PyTorch template and a **network volume** on `/workspace`.
2. Accept the [google/gemma-4-31B-it](https://huggingface.co/google/gemma-4-31B-it) license.
3. Set a write-capable `HF_TOKEN` (and optionally `WANDB_API_KEY`).

### One-shot (`train.sh`)

```bash
cd /workspace/AOS   # after git clone
export HF_TOKEN=hf_...
# export WANDB_API_KEY=...   # optional
bash apps/sft/train.sh

# Overrides:
# EPOCHS=3 bash apps/sft/train.sh
# SEQ_LEN=2048 bash apps/sft/train.sh          # 40GB GPUs
# SKIP_TRAIN=1 bash apps/sft/train.sh          # resume from merge/GGUF
```

Artifacts:

| Step | Path / Hub |
|------|------------|
| LoRA adapter | `/workspace/gemma4-31b-manim-ft` → `nabin2004/AOS-gemma4-31b-manim-sft` |
| Merged bf16 | `/workspace/gemma4-31b-manim-merged` → `nabin2004/AOS-gemma4-31b-manim-merged` |
| GGUF Q4_K_M | `/workspace/gemma4-31b-manim-gguf` → `nabin2004/AOS-gemma4-31b-manim-gguf` |

### Notebook cells (same flow)

```python
# Cell 1 — secrets
import os
os.environ["HF_TOKEN"] = "hf_..."  # required write token
# os.environ["WANDB_API_KEY"] = "..."  # optional
```

```bash
# Cell 2 — clone + deps
!git clone https://github.com/nabin2004/AOS.git /workspace/AOS
%cd /workspace/AOS
!pip install uv
!uv sync --package sft
```

```bash
# Cell 3 — full pipeline
!bash apps/sft/train.sh
```

Infer after training (local adapter):

```bash
!uv run --package sft python apps/sft/infer.py \
  --adapter-dir /workspace/gemma4-31b-manim-ft \
  --runpod \
  --no-tools \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

| Environment | Flag | Default output dir |
|-------------|------|--------------------|
| **RunPod** | `--runpod` | `/workspace/gemma4-31b-manim-ft` |
| Colab | `--colab` (auto when `COLAB_RELEASE_TAG` set) | `/content/drive/MyDrive/gemma4-31b-manim-ft` |
| Kaggle | `--kaggle --output-dir /kaggle/working/...` | notebook output |
| Local | omit flags | `apps/sft/gemma4-31b-manim-ft` |

Notes:

- `--runpod` keeps full defaults (`seq_len=8192`, batch 1, grad accum 8), pins `device_map` to GPU 0, strips multimodal towers, and writes under `/workspace`.
- Attach a network volume at `/workspace` so adapters persist across pod stops.
- `train.sh` builds llama.cpp under `/workspace/llama.cpp` if needed and uses `--skip-ollama-create` (Hub push only).
- Override output with `--output-dir /workspace/my-run` when calling `run.py` directly.

## Run on Google Colab

Colab is fine for smoke tests on smaller Gemma sizes; for full **31B** prefer [RunPod](#run-on-runpod-recommended-for-full-31b). Mount Google Drive **before** training so adapter weights persist after the runtime disconnects. Do **not** use Kaggle `/kaggle/working/...` paths on Colab.

```python
# Cell 1 — mount Drive first (required for persistence)
from google.colab import drive
drive.mount("/content/drive")

import os
os.environ["HF_TOKEN"] = "..."  # Colab secret
```

```bash
# Cell 2 — clone + train
!git clone https://github.com/nabin2004/AOS.git /content/AOS
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
  --adapter-dir /content/gemma4-31b-manim-ft \
  --colab \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

Or infer from the Hub (no local adapter copy):

```bash
!uv run --package sft python apps/sft/infer.py \
  --adapter-dir nabin2004/AOS-gemma4-31b-manim-sft \
  --colab \
  --prompt "Create a short Manim scene explaining eigenvectors in 2D."
```

Notes:

- `--colab` applies the same T4-safe training settings as `--kaggle` (batch 1, seq 2048, no packing) — not suitable for full 31B at seq 8192.
- If Drive is not mounted, output falls back to `/content/gemma4-31b-manim-ft` (ephemeral — lost when runtime disconnects).
- Override output with `--output-dir /content/drive/MyDrive/my-run` or `export SFT_OUTPUT_DIR=...`.

## Run on Kaggle (T4×2) — not recommended for 31B

The `--kaggle` preset targets T4 GPUs and will **warn** when the default base model is `google/gemma-4-31B-it` (needs ~80 GB VRAM). Use [RunPod A100 80GB](#run-on-runpod-recommended-for-full-31b), Vertex ultragpu, or a local A100 80GB+ for full training.

For smoke tests on smaller Gemma 4 sizes only, use a Kaggle notebook with **GPU T4 x2** and pass `--model-id google/gemma-4-E4B-it` explicitly. Add a notebook secret `HF_TOKEN` with a Hugging Face token that has accepted the [google/gemma-4-31B-it](https://huggingface.co/google/gemma-4-31B-it) license.

```bash
export UV_LINK_MODE=copy
export HF_TOKEN=...   # from Kaggle secrets
cd /kaggle/working && git clone https://github.com/<your-org>/AOS.git AOS && cd AOS

uv sync --package sft
uv run --package sft python apps/sft/run.py --kaggle \
  --report-to none \
  --output-dir /kaggle/working/gemma4-31b-manim-ft
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

Optional env vars: `WANDB_ENTITY`, `WANDB_PROJECT_SFT`, `WANDB_RUN_NAME`. Default run name: `gemma4-31b-manim-sft` (group `gemma4-31b-manim`, tags `gemma4-31b,manim,aos,sft`). Disable with `--report-to none`.

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
