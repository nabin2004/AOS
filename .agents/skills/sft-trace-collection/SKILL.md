---
name: sft-trace-collection
description: >-
  Use this skill when generating synthetic prompts, collecting tool-calling trajectories from the Manim coder agent, or preparing SFT/DPO datasets.
---

# SFT Trace Collection & Export

This skill guides the process of collecting and exporting training data from the Code Agent for fine-tuning.

## Workflow

### 1. (Optional) Generate Synthetic Prompts
Generate prompt batches from topic seeds:
```bash
cd apps/agents
uv run python sft_data_gen/generate_prompts.py \
  --num 100 \
  --output sft_data_gen/prompts.jsonl \
  --topics sft_data_gen/topics.txt
```

### 2. Run Batch Trace Collection
Run fast collection (bypasses heavy narration synthesis and OTLP logging):
```bash
cd apps/agents
uv run python sft_data_gen/collect_traces.py \
  --limit 50 \
  --fast \
  --convert-after-local \
  --resume \
  --concurrency 2
```

### 3. Export SFT Dataset
Convert raw trajectories to tool-trace format for LLM training:
```bash
cd apps/agents
uv run python export_local_sft.py
```
Output files are placed in `apps/agents/export_traces/coder_sft/`.

### 4. Upload Dataset to Hugging Face (Optional)
```bash
export HF_TOKEN=your_hf_token
cd apps/sft
uv run python upload_dataset.py
```
