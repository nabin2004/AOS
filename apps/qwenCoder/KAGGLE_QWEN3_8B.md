# Kaggle P100 / T4 End-to-End Pipeline: `Qwen/Qwen3-8B`

Complete end-to-end SFT fine-tuning, adapter merging, multi-quantization GGUF export (`Q4_K_M` and `Q8_0`), and dual Hugging Face repository upload pipeline for **`Qwen/Qwen3-8B`** on **Kaggle P100 (16 GB) / T4 GPUs**.

---

## Datasets & Curated Mix

The training pipeline fine-tunes on the gold-standard dataset:
- **Dataset**: [`nabin2004/qwen3-8b-manimator-gold-sft`](https://huggingface.co/datasets/nabin2004/qwen3-8b-manimator-gold-sft)
- **Size**: **733 gold samples** in standard chat format (`messages: [system, user, assistant]`).
- **Pedagogical Features**:
  1. Complete `<Plan>` blocks specifying visual goals, keyframes, mathematical formulas, and required animation components.
  2. Executable **Manim CE** scripts with **`VoiceoverScene`** architecture and precision audio bookmark synchronization (`wait_until_bookmark`).
  3. Clean API compliance with up-to-date Manim Community Edition standards.

---

## Hardware Specifications & Compatibility

| Setting | Value |
|---------|--------|
| **Accelerator** | GPU P100 (16 GB VRAM, Pascal `sm_60`) or T4 (16 GB VRAM, Turing `sm_75`) |
| **Internet** | On |
| **Session Length** | ~9 hours (Training takes ~35 minutes for 3 epochs) |
| **Precision** | QLoRA 4-bit (`nf4`), `fp16` compute, FP32 adapter dtypes |
| **Optimizer** | `paged_adamw_8bit` |
| **Sequence Length** | `4096` (Covers 100% of gold dataset examples without truncation) |
| **Epochs** | `3` (~275 total optimizer steps with batch size 1 and grad accum 8) |
| **Checkpointing** | Every `50` steps |
| **Packing** | Disabled (`--no-packing` avoids cross-sample contamination without Flash Attention) |

> [!NOTE]
> Kaggle P100 GPUs (`sm_60`) do not natively support `bf16` or Flash Attention. The script pins **system PyTorch `2.7.1+cu118`** to prevent PyPI CUDA 13 binary incompatibility errors.

---

## Required Secrets (Kaggle Notebook Add-ons → Secrets)

| Secret Key | Purpose | Required |
|------------|---------|----------|
| `HF_TOKEN` | Hugging Face **write** token for pushing adapter, merged weights, and GGUF repositories | **Yes** |
| `WANDB_API_KEY` | Weights & Biases logging | Optional |

In your Kaggle notebook, export secrets in the **first Python cell**:

```python
import os
from kaggle_secrets import UserSecretsClient

secrets = UserSecretsClient()
os.environ["HF_TOKEN"] = secrets.get_secret("HF_TOKEN")

try:
    os.environ["WANDB_API_KEY"] = secrets.get_secret("WANDB_API_KEY")
except Exception:
    print("WANDB_API_KEY not found; training metrics will log locally.")
```

---

## One-Click Super Simple Notebook Code

In a Kaggle Notebook code cell (Bash or Python), simply run:

```python
!cd /kaggle/working && git clone https://github.com/nabin2004/AOS.git 2>/dev/null || git -C /kaggle/working/AOS pull
!python3 /kaggle/working/AOS/apps/qwenCoder/run_kaggle.py
```

> [!TIP]
> `run_kaggle.py` automatically:
> 1. Extracts `HF_TOKEN` from Kaggle Secrets (Add-ons → Secrets).
> 2. Skips downloading 2.5 GB of PyTorch wheels if existing PyTorch already works on CUDA.
> 3. Streams `nabin2004/qwen3-8b-manimator-gold-sft` directly from Hugging Face Datasets.
> 4. Runs QLoRA SFT (3 epochs, seq_len 4096, 4-bit NF4).
> 5. Merges LoRA adapter into full bf16 base model weights.
> 6. Quantizes merged model to GGUFs (`Q4_K_M` & `Q8_0`) and pushes all releases to Hugging Face!

---

## Outputs & Hugging Face Repositories

| Artifact | Output Location / Hugging Face Repository |
|----------|-------------------------------------------|
| **Gold Dataset** | [`nabin2004/qwen3-8b-manimator-gold-sft`](https://huggingface.co/datasets/nabin2004/qwen3-8b-manimator-gold-sft) |
| **LoRA Adapter** | [`nabin2004/AOS-qwen3-8b-adapter`](https://huggingface.co/nabin2004/AOS-qwen3-8b-adapter) |
| **Merged Base Model** | [`nabin2004/AOS-Qwen3-8B-Merged`](https://huggingface.co/nabin2004/AOS-Qwen3-8B-Merged) |
| **Quantized GGUFs & Modelfile** | [`nabin2004/AOS-Qwen3-8B-GGUF`](https://huggingface.co/nabin2004/AOS-Qwen3-8B-GGUF) (`Q4_K_M` & `Q8_0`) |

---

## Custom CLI Options & Environment Overrides

You can pass command-line arguments to `run_kaggle.py`:

```bash
python3 /kaggle/working/AOS/apps/qwenCoder/run_kaggle.py \
  --dataset-repo nabin2004/qwen3-8b-manimator-gold-sft \
  --epochs 3 \
  --seq-len 4096 \
  --save-steps 50 \
  --hub-adapter-repo nabin2004/AOS-qwen3-8b-adapter \
  --hub-merged-repo nabin2004/AOS-Qwen3-8B-Merged \
  --hub-gguf-repo nabin2004/AOS-Qwen3-8B-GGUF
```

Or via environment variables when running `kaggle_qwen3_8b_e2e.sh`:

```bash
DATASET_REPO="nabin2004/qwen3-8b-manimator-gold-sft"
EPOCHS=3
SEQ_LEN=4096
SAVE_STEPS=50
bash /kaggle/working/AOS/apps/qwenCoder/kaggle_qwen3_8b_e2e.sh
```
