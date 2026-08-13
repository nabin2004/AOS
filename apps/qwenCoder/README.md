# AOS Qwen2.5-Coder finetuning + OpenCode bridge

End-to-end path for **local Ollama / OpenCode** Manim agents:

1. Collect Code Agent trajectories (video + audio)
2. Export `tool_trace` SFT + DPO preference pairs
3. SFT → DPO → GRPO on `Qwen/Qwen2.5-Coder-7B-Instruct`
4. Merge → llama.cpp GGUF → Hugging Face → Ollama → OpenCode

Gemma pipeline under [`apps/sft`](../sft/) is unchanged.

---

## Architecture

```text
OpenCode (Qwen / Ollama)
   └─ .opencode/tools/aos.ts  →  animus animate --json
         └─ PydanticAI Code Agent → Manim + Voiceover → MP4
               └─ trajectories.jsonl
```

Repo root:

- [`opencode.json`](../../opencode.json) — Ollama provider
- [`.opencode/tools/aos.ts`](../../.opencode/tools/aos.ts) — `generate_educational_video` tool

```bash
# Generate a video via CLI (same contract OpenCode uses)
cd apps/agents
AOS_MODEL_PROFILE=local AOS_CODER_MODEL=ollama:qwen2.5-coder:7b \
  uv run python cli.py animate "Explain backpropagation" --json --output-dir ./outputs/backprop
```

JSON fields: `ok`, `video_path`, `scene_path`, `run_dir`, `has_audio`, `trajectory_path`, `error`.

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

## Train order

```text
SFT (tool_trace) → DPO (preference) → GRPO (rewards) → merge → GGUF → HF → Ollama → OpenCode
```

### 1. SFT

```bash
cd apps/qwenCoder
uv sync
uv run python preflight_qwen.py
bash train.sh
# or:
uv run python run.py --data-path ../agents/export_traces/coder_sft/tool_trace.train.jsonl --push-to-hub
uv run python merge_adapter.py --adapter-dir ./qwen2.5-coder-7b-manim-ft --output-dir ./qwen2.5-coder-7b-manim-merged --push-to-hub
uv run python export_gguf.py --model-dir ./qwen2.5-coder-7b-manim-merged --output-dir ./qwen2.5-coder-7b-manim-gguf --push-to-hub
```

### 2. DPO

```bash
cd apps/dpo
uv sync
uv run python run.py \
  --sft-lora ../qwenCoder/qwen2.5-coder-7b-manim-ft \
  --data-path ../agents/export_traces/coder_sft/preference/train.jsonl \
  --push-to-hub
```

### 3. GRPO

```bash
cd apps/grpo
uv sync
uv run python run.py --base qwen \
  --sft-lora ../qwenCoder/qwen2.5-coder-7b-manim-ft \
  --prompts-path ../agents/sft_data_gen/prompts_curriculum_200.jsonl
uv run python package_adapter.py --base qwen --adapter-dir ./grpo_qwen_manim --push-to-hub
```

### 4. Serve in OpenCode

```bash
ollama create aos-qwen2.5-coder-7b-manim -f apps/qwenCoder/qwen2.5-coder-7b-manim-gguf/Modelfile
# Select model aos-qwen2.5-coder-7b-manim in OpenCode (see opencode.json)
```

---

## Hub IDs

| Artifact | Repo |
|----------|------|
| Dataset | `nabin2004/AOS-Qwen-Trajectories` |
| SFT adapter | `nabin2004/AOS-qwen2.5-coder-7b-manim-sft` |
| Merged | `nabin2004/AOS-qwen2.5-coder-7b-manim-merged` |
| GGUF | `nabin2004/AOS-qwen2.5-coder-7b-manim-gguf` |
| DPO | `nabin2004/AOS-qwen2.5-coder-7b-manim-dpo` |

---

## Layout

| Path | Role |
|------|------|
| `run.py` / `train.sh` | QLoRA SFT e2e |
| `merge_adapter.py` / `export_gguf.py` | Deploy packaging |
| `collect_and_export.sh` | Ollama data loop |
| `upload_dataset.py` | HF dataset push |
| `preflight_qwen.py` | Tool chat-template gate |
| `identity.py` | Shared names |
| `chat-template.ipynb` | Exploratory notebook (kept) |
