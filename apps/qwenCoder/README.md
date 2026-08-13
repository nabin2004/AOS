# AOS Qwen2.5-Coder finetuning + OpenCode bridge

End-to-end path for **local Ollama / OpenCode** Manim agents on `Qwen/Qwen2.5-Coder-7B-Instruct`:

1. Collect Code Agent trajectories (optional) + preference pairs
2. **Staged SFT** → **DPO** → **GRPO (ManiBench)**
3. Merge → llama.cpp GGUF → Hugging Face → Ollama → OpenCode

Gemma pipeline under [`apps/sft`](../sft/) is unchanged.

---

## Staged train order

```text
SFT-1 manim-sft
  → SFT-2 educlaw-manim-sft (20k subsample, continue LoRA)
  → SFT-3 AOS-Trajectories tool_trace (continue LoRA)
  → DPO preference pairs
  → GRPO ManiBench rewards
  → merge → GGUF → HF → Ollama → OpenCode
```

| Stage | Dataset | Notes |
|-------|---------|-------|
| SFT-1 | [`nabin2004/manim-sft`](https://huggingface.co/datasets/nabin2004/manim-sft) | General Manim CE codegen (~38k) |
| SFT-2 | [`nabin2004/educlaw-manim-sft`](https://huggingface.co/datasets/nabin2004/educlaw-manim-sft) | API/curriculum; default max **20k** |
| SFT-3 | [`nabin2004/AOS-Trajectories`](https://huggingface.co/datasets/nabin2004/AOS-Trajectories) `tool_trace/train.jsonl` | Agent tool-calling traces |
| DPO | local `export_traces/coder_sft/preference/*.jsonl` | Chosen/rejected pairs |
| GRPO | [`nabin2004/ManiBench`](https://huggingface.co/datasets/nabin2004/ManiBench) | Visual-event / coverage / VCER rewards |

One LoRA is continue-trained across SFT stages (`--init-adapter`). DPO trains a new adapter from the final SFT. GRPO stacks on the **DPO** adapter when present (else SFT).

### One-shot orchestrator

```bash
cp apps/training/.env.example apps/training/.env   # set WANDB_API_KEY
export HF_TOKEN=hf_...
bash apps/qwenCoder/train_stages.sh

# Smoke (tiny overfit each stage):
SMOKE=1 bash apps/qwenCoder/train_stages.sh

# Skip / package knobs:
SKIP_DPO=1 SKIP_GRPO=1 bash apps/qwenCoder/train_stages.sh
RUN_MERGE=1 RUN_GGUF=1 PUSH_TO_HUB=1 bash apps/qwenCoder/train_stages.sh
```

### Manual stage commands

```bash
cd apps/qwenCoder && uv sync

# SFT-1
uv run python run.py --dataset-repo nabin2004/manim-sft --stage manim

# SFT-2 (continue)
uv run python run.py \
  --dataset-repo nabin2004/educlaw-manim-sft \
  --max-samples 20000 \
  --init-adapter ./qwen2.5-coder-7b-manim-ft \
  --stage educlaw

# SFT-3 (continue)
uv run python run.py \
  --dataset-repo nabin2004/AOS-Trajectories \
  --dataset-file tool_trace/train.jsonl \
  --init-adapter ./qwen2.5-coder-7b-manim-ft \
  --stage traces

# DPO
cd ../dpo && uv sync
uv run python run.py \
  --sft-lora ../qwenCoder/qwen2.5-coder-7b-manim-ft \
  --data-path ../agents/export_traces/coder_sft/preference/train.jsonl

# GRPO (ManiBench by default — do not pass --prompts-path unless overriding)
cd ../grpo && uv sync
uv run python run.py --base qwen \
  --sft-lora ../dpo/qwen2.5-coder-7b-manim-dpo
uv run python package_adapter.py --base qwen --adapter-dir ./grpo_qwen_manim --push-to-hub
```

Legacy single-dataset e2e (tool_trace only): `bash train.sh`.

---

## Weights & Biases

Defaults to **wandb** when `WANDB_API_KEY` is set (via [`apps/training/wandb_env.py`](../training/wandb_env.py)).

```bash
cp apps/training/.env.example apps/training/.env
# edit: WANDB_API_KEY, WANDB_ENTITY
```

| Stage | Project env | Default project | Run name |
|-------|-------------|-----------------|----------|
| SFT | `WANDB_PROJECT_QWEN_SFT` | `aos-qwen-sft` | `…-sft-manim` / `…-educlaw` / `…-traces` |
| DPO | `WANDB_PROJECT_DPO` | `aos-dpo` | `qwen2.5-coder-7b-manim-dpo` |
| GRPO | `WANDB_PROJECT_GRPO` | `aos-grpo` | `qwen2.5-coder-7b-manim-grpo` |

Disable: `--report-to none` or `REPORT_TO=none`.

---

## Data collection (Ollama)

```bash
bash apps/qwenCoder/collect_and_export.sh
PUSH=1 bash apps/qwenCoder/collect_and_export.sh   # upload nabin2004/AOS-Qwen-Trajectories
```

Or step-by-step:

```bash
export AOS_MODEL_PROFILE=local
export AOS_CODER_MODEL=ollama:qwen2.5-coder:7b
cd apps/agents
uv run python sft_data_gen/collect_traces.py --prompts sft_data_gen/prompts_curriculum_200.jsonl
uv run python export_local_sft.py --format tool_trace --train-split 0.9
uv run python build_preference_pairs.py
```

Gold filter: `success=true` and `has_audio=true` (see `TrajectoryRecord.has_audio`).

---

## Architecture

```text
OpenCode (Qwen / Ollama)
   └─ .opencode/tools/aos.ts  →  animus animate --json
         └─ PydanticAI Code Agent → Manim + Voiceover → MP4
               └─ trajectories.jsonl
```

```bash
cd apps/agents
AOS_MODEL_PROFILE=local AOS_CODER_MODEL=ollama:qwen2.5-coder:7b \
  uv run python cli.py animate "Explain backpropagation" --json --output-dir ./outputs/backprop
```

---

## Serve in OpenCode

```bash
ollama create aos-qwen2.5-coder-7b-manim -f apps/qwenCoder/qwen2.5-coder-7b-manim-gguf/Modelfile
# Select model aos-qwen2.5-coder-7b-manim in OpenCode (see opencode.json)
```

---

## Hub IDs

| Artifact | Repo |
|----------|------|
| SFT chat data | `nabin2004/manim-sft` |
| Curriculum data | `nabin2004/educlaw-manim-sft` |
| Trajectories | `nabin2004/AOS-Trajectories` |
| Qwen trajectories | `nabin2004/AOS-Qwen-Trajectories` |
| GRPO benchmark | `nabin2004/ManiBench` |
| SFT adapter | `nabin2004/AOS-qwen2.5-coder-7b-manim-sft` |
| Merged | `nabin2004/AOS-qwen2.5-coder-7b-manim-merged` |
| GGUF | `nabin2004/AOS-qwen2.5-coder-7b-manim-gguf` |
| DPO | `nabin2004/AOS-qwen2.5-coder-7b-manim-dpo` |

---

## Layout

| Path | Role |
|------|------|
| `run.py` / `train_stages.sh` | Staged SFT curriculum + DPO/GRPO orchestrator |
| `train.sh` | Legacy single-dataset SFT → merge → GGUF |
| `merge_adapter.py` / `export_gguf.py` | Deploy packaging |
| `collect_and_export.sh` | Ollama data loop |
| `upload_dataset.py` | HF dataset push |
| `preflight_qwen.py` | Tool chat-template gate |
| `identity.py` | Shared names + W&B stage tags |
| `chat-template.ipynb` | Exploratory notebook (kept) |
