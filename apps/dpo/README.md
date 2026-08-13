# AOS DPO

Preference fine-tuning on Code Agent trajectories (`chosen` vs `rejected`).

## Data

Build pairs from collected runs:

```bash
cd apps/agents
uv run python build_preference_pairs.py
```

## Train

```bash
cd apps/dpo
uv sync
uv run python run.py \
  --sft-lora ../qwenCoder/qwen2.5-coder-7b-manim-ft \
  --data-path ../agents/export_traces/coder_sft/preference/train.jsonl \
  --push-to-hub
```

After DPO, merge + GGUF via the Qwen packaging scripts:

```bash
cd apps/qwenCoder
uv run python merge_adapter.py \
  --adapter-dir ../dpo/qwen2.5-coder-7b-manim-dpo \
  --output-dir ./qwen2.5-coder-7b-manim-merged-dpo
uv run python export_gguf.py \
  --model-dir ./qwen2.5-coder-7b-manim-merged-dpo \
  --output-dir ./qwen2.5-coder-7b-manim-gguf-dpo
```
