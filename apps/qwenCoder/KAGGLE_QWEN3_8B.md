# Kaggle P100 End-to-End Pipeline: `Qwen/Qwen3-8B`

Complete end-to-end SFT fine-tuning, adapter merging, multi-quantization GGUF export (`Q4_K_M` and `Q8_0`), and dual Hugging Face repository upload pipeline for **`Qwen/Qwen3-8B`** on **Kaggle P100 GPUs (16 GB VRAM)**.

---

## Datasets & Curated Mix

The training pipeline uses the combined single-pass **~5,400-sample dataset** ([`nabin2004/manim-aos-5k400`](https://huggingface.co/datasets/nabin2004/manim-aos-5k400)):
1. **5,000 Targeted Manim Code Examples**: API grounding, traceback error corrections, updaters, scientific compute (`numpy`, `scipy`, `sympy`), and pedagogical LaTeX scenes.
2. **400 AOS Agent Trajectories**: Multi-turn tool calling and neural network visualization prompts (Andrej Karpathy prompt suite).

---

## Hardware Specifications & Compatibility

| Setting | Value |
|---------|--------|
| **Accelerator** | GPU P100 (16 GB VRAM, Pascal `sm_60`) |
| **Internet** | On |
| **Session Length** | ~9 hours |
| **Precision** | QLoRA 4-bit (`nf4`), `fp16` compute, FP32 adapter dtypes |
| **Optimizer** | `paged_adamw_8bit` |
| **Sequence Length** | `2048` |
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
> 3. Curates the 5.4k dataset automatically if not present.
> 4. Runs QLoRA SFT, adapter merging, GGUF multi-quantization (`Q4_K_M` & `Q8_0`), and pushes all artifacts to HuggingFace!

---

## Outputs & Hugging Face Repositories

| Artifact | Output Location / Hugging Face Repository |
|----------|-------------------------------------------|
| **Curated Dataset** | [`nabin2004/manim-aos-5k400`](https://huggingface.co/datasets/nabin2004/manim-aos-5k400) |
| **LoRA Adapter** | [`nabin2004/AOS-qwen3-8b-adapter`](https://huggingface.co/nabin2004/AOS-qwen3-8b-adapter) |
| **Merged Base Model** | [`nabin2004/AOS-Qwen3-8B-Merged`](https://huggingface.co/nabin2004/AOS-Qwen3-8B-Merged) |
| **Quantized GGUFs & Modelfile** | [`nabin2004/AOS-Qwen3-8B-GGUF`](https://huggingface.co/nabin2004/AOS-Qwen3-8B-GGUF) (`Q4_K_M` & `Q8_0`) |

---

## Custom Environment Overrides

You can prefix environment variables before invoking the bash script:

```bash
MODEL_ID="Qwen/Qwen3-8B"
DATASET_REPO="nabin2004/manim-aos-5k400"
HUB_ADAPTER_REPO="nabin2004/AOS-qwen3-8b-adapter"
HUB_MERGED_REPO="nabin2004/AOS-Qwen3-8B-Merged"
HUB_GGUF_REPO="nabin2004/AOS-Qwen3-8B-GGUF"
EPOCHS=1
SEQ_LEN=2048
SAVE_STEPS=200
```
