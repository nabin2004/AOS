# Kaggle T4×2: qwen-Manimator-1 SFT Pipeline

Complete end-to-end SFT fine-tuning, adapter merging, multi-quantization GGUF export, and dual HF Hub upload for **`Qwen/Qwen3-8B`** on **Kaggle T4×2 GPUs (2×16 GB VRAM)**.

---

## Outputs & Hugging Face Repositories

| Artifact | HF Repository |
|---|---|
| **Dataset** | [`nabin2004/qwen-Manimator-1-sft-data`](https://huggingface.co/datasets/nabin2004/qwen-Manimator-1-sft-data) |
| **LoRA Adapter** | [`nabin2004/qwen-Manimator-1-sft`](https://huggingface.co/nabin2004/qwen-Manimator-1-sft) |
| **Merged Model** | [`nabin2004/qwen-Manimator-1-merged`](https://huggingface.co/nabin2004/qwen-Manimator-1-merged) |
| **Quantized GGUFs** | [`nabin2004/qwen-Manimator-1-gguf`](https://huggingface.co/nabin2004/qwen-Manimator-1-gguf) (`Q4_K_M` & `Q8_0`) |

---

## Hardware Specifications

| Setting | Value |
|---|---|
| **Accelerator** | GPU T4 × 2 (2 × 16 GB VRAM, Turing `sm_75`) |
| **Internet** | On |
| **Session Length** | ~9 hours |
| **Precision** | QLoRA 4-bit (`nf4`), `fp16` compute |
| **Optimizer** | `paged_adamw_8bit` |
| **Sequence Length** | `4500` |
| **Effective Batch** | 1 × 8 (grad_accum) × 2 GPUs = **16** |
| **LoRA** | r=16, alpha=32 |
| **Warmup** | ratio=0.05 (cosine) |
| **Packing** | Disabled |

> [!NOTE]
> T4 GPUs (sm_75) do **not** natively support `bf16`. The pipeline automatically uses `fp16` (detected via `apply_gpu_precision()`).

---

## Required Kaggle Secrets

Add these under **Add-ons → Secrets** in your Kaggle notebook:

| Secret Key | Purpose | Required |
|---|---|---|
| `HF_TOKEN` | Hugging Face **write** token for pushing adapter, merged, GGUF | **Yes** |
| `WANDB_API_KEY` | Weights & Biases run logging | Optional |

Export secrets in your first notebook cell:
```python
import os
from kaggle_secrets import UserSecretsClient

secrets = UserSecretsClient()
os.environ["HF_TOKEN"] = secrets.get_secret("HF_TOKEN")

try:
    os.environ["WANDB_API_KEY"] = secrets.get_secret("WANDB_API_KEY")
except Exception:
    print("WANDB_API_KEY not found; skipping W&B logging.")
```

---

## One-Click Notebook Code

In a Kaggle Notebook code cell:

```python
# Clone / pull the AOS repository
!cd /kaggle/working && git clone https://github.com/nabin2004/AOS.git 2>/dev/null || git -C /kaggle/working/AOS pull

# Run the Manimator-1 pipeline
!python3 /kaggle/working/AOS/apps/qwenCoder/run_kaggle_manimator1.py
```

> [!TIP]
> `run_kaggle_manimator1.py` automatically:
> 1. Retrieves `HF_TOKEN` and `WANDB_API_KEY` from Kaggle Secrets.
> 2. Checks PyTorch CUDA — skips 2.5 GB reinstall if already working.
> 3. Uploads the dataset (`apps/new_data/train.jsonl`) to `nabin2004/qwen-Manimator-1-sft-data`.
> 4. Runs QLoRA SFT (3 epochs, seq_len=4500, lr=1e-4, LoRA r=16).
> 5. Merges adapter into base weights & pushes merged model.
> 6. Converts to GGUF Q4_K_M + Q8_0 & pushes GGUF repository.

---

## Training Config (Full Details)

| Parameter | Value |
|---|---|
| `num_train_epochs` | 3 |
| `per_device_train_batch_size` | 1 |
| `gradient_accumulation_steps` | 8 |
| `learning_rate` | 1e-4 |
| `lr_scheduler_type` | cosine |
| `warmup_ratio` | 0.05 |
| `optim` | paged_adamw_8bit |
| `max_length` | 4500 |
| `packing` | False |
| `save_strategy` | epoch |
| `bf16` | False (auto-detected; T4 uses fp16) |
| `fp16` | True |
| `gradient_checkpointing` | True |
| `assistant_only_loss` | True |
| `report_to` | wandb |
| `run_name` | `qwen-Manimator-1-sft` |
| `wandb_project` | `aos-qwen-sft` |

---

## Custom Overrides

```bash
python3 run_kaggle_manimator1.py \
  --epochs 2 \
  --seq-len 4500 \
  --skip-upload-dataset \
  --skip-gguf
```

Available flags:
- `--epochs N` — override epoch count (default: 3)
- `--seq-len N` — override max sequence length (default: 4500)
- `--max-samples N` — limit training samples (0 = all)
- `--skip-upload-dataset` — do not push dataset to HF Hub
- `--skip-train` — skip SFT phase (resume from existing adapter)
- `--skip-merge` — skip merge phase
- `--skip-gguf` — skip GGUF quantization
- `--no-push` — dry run (no HF Hub pushes at all)
- `--force-reinstall-torch` — force PyTorch cu118 reinstall

---

## After Training

```bash
# Test the merged model
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained("nabin2004/qwen-Manimator-1-merged", device_map="auto")

# Or run with Ollama
ollama run hf.co/nabin2004/qwen-Manimator-1-merged
ollama run hf.co/nabin2004/qwen-Manimator-1-gguf
```
