# Local Fine-Tuning Guide for NVIDIA RTX 3060 (12 GB VRAM)

This guide details how to fine-tune open-source LLMs (1.5B to 8B parameters) for **ManimCE Python code generation** using the AOS platform locally on an **NVIDIA GeForce RTX 3060 (12 GB VRAM)**.

---

## 1. VRAM Capability & Model Selection

The RTX 3060 features Ampere architecture (`sm_86`), which provides native support for **BF16**, **Flash Attention / SDPA**, and **4-bit NF4 Quantization (bitsandbytes)**.

| Model Class | Examples | Feasible Setup | Recommended Context Window | Estimated VRAM |
| --- | --- | --- | --- | --- |
| **Small (1.5B–3B)** | `Qwen2.5-Coder-1.5B` / `3B`, `Llama-3.2-3B` | **16-bit LoRA** or **4-bit QLoRA** | 2048 – 4096 tokens | 4 GB – 7 GB |
| **Mid-Size (7B–8B)** | `Qwen2.5-Coder-7B`, `Llama-3.1-8B`, `DeepSeek-Coder-6.7B` | **4-bit QLoRA (NF4)** | 1024 – 2048 tokens | 8 GB – 10.5 GB |

> [!TIP]
> **Recommended Starting Point:** Start with **`Qwen/Qwen2.5-Coder-1.5B-Instruct`** or **`Qwen/Qwen2.5-Coder-7B-Instruct`**. Code-focused base models already master Python syntax and quickly acquire ManimCE classes, vector positions, and scene animations.

---

## 2. Environment Setup

Make sure you have installed NVIDIA drivers with CUDA 12.x support and `uv` package manager.

```bash
# Clone and navigate to repository root
cd AOS

# Synchronize virtual environment & workspace dependencies
uv sync
```

---

## 3. Supervised Fine-Tuning (SFT)

Supervised Fine-Tuning trains the model on paired text-to-code dataset trajectories (e.g. natural language prompts $\rightarrow$ executable ManimCE Python code).

### 3.1 Training Qwen2.5-Coder (`apps/qwenCoder`)

Navigate to the QwenCoder app directory:

```bash
cd apps/qwenCoder
```

#### Run 4-bit QLoRA Fine-Tuning with `--rtx3060` Preset:

- **For 7B models** (e.g. `Qwen2.5-Coder-7B-Instruct`):
  ```bash
  uv run python run.py --rtx3060 --stage manim
  ```
- **For 1.5B or 3B models** (e.g. `Qwen2.5-Coder-1.5B-Instruct`):
  ```bash
  uv run python run.py --rtx3060 --model-id Qwen/Qwen2.5-Coder-1.5B-Instruct --seq-len 4096 --stage manim
  ```
- **Using a local custom trajectory dataset**:
  ```bash
  uv run python run.py --rtx3060 --data-path ../agents/export_traces/coder_sft/sft/train.jsonl
  ```

### 3.2 Training Gemma / General SFT (`apps/sft`)

```bash
cd apps/sft
uv run python run.py --rtx3060
```

> [!NOTE]
> The `--rtx3060` preset automatically enforces:
> - `per_device_train_batch_size = 1`
> - `gradient_accumulation_steps = 8` (effective batch size of 8)
> - `use_4bit = True` (NF4 Double Quantization)
> - `optim = "paged_adamw_8bit"`
> - `gradient_checkpointing = True`
> - `use_bf16 = True` (Ampere native precision)

---

## 4. Direct Preference Optimization (DPO)

DPO optimizes model output quality by training on preference pairs (syntactically clean, runnable Manim animations vs. broken or hallucinated code).

```bash
cd apps/dpo

# Train DPO adapter starting from your local SFT adapter
uv run python run.py --rtx3060 --sft-lora ../qwenCoder/qwen2.5-coder-7b-manim-ft
```

---

## 5. Group Relative Policy Optimization (GRPO)

GRPO runs multi-sample rollouts against Manim compile and lint reward metrics. Running GRPO on a 12 GB GPU requires strict rollout limits to prevent VRAM Out-Of-Memory (OOM) errors.

```bash
cd apps/grpo

# Run GRPO with 12GB VRAM guardrails (2 generations, max 512 completion tokens)
uv run python run.py --rtx3060 --base qwen
```

---

## 6. Model Export: GGUF & Ollama Integration

Once training is complete, convert your LoRA adapter and deploy it locally to Ollama for interactive agent usage.

### 6.1 Merge LoRA Adapter

```bash
cd apps/qwenCoder

# Merge 4-bit adapter into 16-bit FP16 base model
uv run python merge_adapter.py \
  --adapter-path ./qwen2.5-coder-7b-manim-ft \
  --output-dir ./merged_model
```

### 6.2 Convert to GGUF & Quantize

```bash
uv run python export_gguf.py \
  --model-dir ./merged_model \
  --quantization Q4_K_M \
  --output ./manim-qwen2.5-coder-7b-q4_k_m.gguf
```

### 6.3 Deploy to Local Ollama Service

Create a `Modelfile`:
```dockerfile
FROM ./manim-qwen2.5-coder-7b-q4_k_m.gguf
PARAMETER stop "<|im_end|>"
PARAMETER temperature 0.2
SYSTEM "You are an expert ManimCE Python code generator."
```

Create and run the Ollama model:
```bash
ollama create manim-coder -f Modelfile
ollama run manim-coder "Create a Manim animation showing a rotating sine wave"
```

---

## 7. VRAM Optimization & Troubleshooting Tips

If you encounter CUDA Out-Of-Memory (`CUDA out of memory`) errors on your 12 GB RTX 3060:

1. **Enable PyTorch Expandable Segments**:
   Set environment variable prior to execution:
   ```bash
   # Windows PowerShell
   $env:PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"

   # Linux / Bash
   export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
   ```
2. **Reduce Sequence Length (`--seq-len`)**:
   - For 7B models: set `--seq-len 1024` or `--seq-len 1536`.
   - For 1.5B/3B models: set `--seq-len 2048`.
3. **Use 8-bit Paged Optimizer**:
   Ensure `optim = "paged_adamw_8bit"` is enabled (handled automatically by `--rtx3060`).
4. **Disable Vision/Multimodal Towers**:
   Ensure multimodal vision towers are stripped (`strip_multimodal_towers=True`).
