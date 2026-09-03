# End-to-End GRPO Execution Guide

Comprehensive guide for training the **ManiBench-GRPO** policy model for mathematical animation and voiceover synthesis across **Kaggle GPU Instances (Dual T4 / P100)** and **Local Workstations**.

---

## 1. Quickstart: Kaggle GPU (Recommended)

Kaggle provides free access to **Dual NVIDIA T4 GPUs (2x 16 GB = 32 GB VRAM)**, which is ideal for GRPO rollouts and 4-bit QLoRA training.

### Step 1: Create Notebook & Configure Hardware
1. Navigate to [kaggle.com/code](https://www.kaggle.com/code) → **New Notebook**.
2. In the right-hand sidebar (**Notebook options**):
   - **Accelerator**: Select **GPU T4 x 2** (or GPU P100).
   - **Internet**: Toggle to **ON** (required for downloading dataset splits and Hugging Face weights).

### Step 2: Add Secrets (HF_TOKEN & WANDB_API_KEY)
1. In the Kaggle top menu: **Add-ons** → **Secrets**.
2. Add your tokens:
   - `HF_TOKEN`: Your Hugging Face user access token (with `write` permissions to push the trained adapter).
   - `WANDB_API_KEY`: *(Optional but recommended)* Your Weights & Biases API key for live loss, reward breakdown, and learning curves.

### Step 3: Run the Training Cell
Paste and execute the following in a single notebook cell:

```python
# 1. Clone the repository and pull the latest code
!git clone https://github.com/nabin2004/AOS.git
%cd AOS
!git pull origin master

# 2. Run End-to-End GRPO Stacking on top of the DPO Adapter
!python3 apps/grpo/run_kaggle_grpo.py \
    --base-model Qwen/Qwen3-8B \
    --sft-lora nabin2004/AOS-qwen3-8b-narrated-dpo \
    --dataset-repo nabin2004/Manim-grpo-dataset-200 \
    --hub-repo nabin2004/AOS-qwen3-8b-grpo \
    --push-to-hub
```

---

## 2. Quick Verification (Smoke Test)

To verify the entire environment, dataset indexing, and CUDA allocation in 30 seconds before launching a full training run:

```python
!python3 apps/grpo/run_kaggle_grpo.py --smoke --report-to none
```

---

## 3. Running with Live OpenCLIP Visual Rewards

If you want GRPO rollouts to be evaluated with real headless Manim rendering and **live OpenCLIP frame similarity** (in addition to lexical checks):

```python
!python3 apps/grpo/run_kaggle_grpo.py \
    --base-model Qwen/Qwen3-8B \
    --sft-lora nabin2004/AOS-qwen3-8b-narrated-dpo \
    --dataset-repo nabin2004/Manim-grpo-dataset-200 \
    --render \
    --push-to-hub
```

---

## 4. Running Locally on Workstations (RTX 3060 / 3090 / 4090)

### Step 1: Environment Setup
```bash
cd apps/grpo
uv sync
```

### Step 2: Set Environment Variables
```bash
# In Windows PowerShell:
$env:HF_TOKEN="your_hf_token_here"
$env:WANDB_API_KEY="your_wandb_api_key_here"

# In Linux / macOS Bash:
export HF_TOKEN="your_hf_token_here"
export WANDB_API_KEY="your_wandb_api_key_here"
```

### Step 3: Launch Local GRPO Training
```bash
# For 12 GB VRAM GPUs (e.g. RTX 3060):
uv run python run.py --base qwen --rtx3060

# For 24 GB VRAM GPUs (e.g. RTX 3090 / 4090):
uv run python run.py \
    --base qwen \
    --base-model Qwen/Qwen3-8B \
    --sft-lora nabin2004/AOS-qwen3-8b-narrated-dpo \
    --repeat-factor 10 \
    --num-generations 4
```

---

## 5. CLI Parameter Reference

| Parameter | Description | Default Value |
|---|---|---|
| `--base-model` | Base Hugging Face model architecture | `Qwen/Qwen3-8B` |
| `--sft-lora` | Initial policy adapter (local path or HF repo ID) | `nabin2004/AOS-qwen3-8b-narrated-dpo` |
| `--dataset-repo` | Hugging Face Hub dataset repo containing problem bundles | `nabin2004/Manim-grpo-dataset-200` |
| `--hub-repo` | Hugging Face target model repo for final GRPO LoRA | `nabin2004/AOS-qwen3-8b-grpo` |
| `--push-to-hub` | Automatically upload trained adapter upon completion | `False` |
| `--smoke` | Single-step optimization for environment verification | `False` |
| `--max-steps` | Explicit cap on training steps | `None` (full epochs) |
| `--render` | Enable live headless Manim rendering & OpenCLIP visual scoring | `False` (fast lexical heuristic) |
| `--dual-t4` | Activate Dual-T4 multi-GPU sampling preset (32 GB VRAM) | Auto-detected in Kaggle script |
| `--p100` | Activate Single-GPU memory preset (16 GB VRAM) | Auto-detected in Kaggle script |
| `--report-to` | Telemetry backend (`wandb` or `none`) | `wandb` |
| `--run-name` | Custom name for W&B logging stream | `qwen3-8b-manim-dpo-grpo` |

---

## 6. Live Telemetry on Weights & Biases (W&B)

When `--report-to wandb` is active, you can track the following real-time metrics in your W&B dashboard under project **`aos-grpo`**:

- `reward/exec`: Executability rate (syntax correctness + scene class structure).
- `reward/align`: Composite alignment (lexical presence + OpenCLIP temporal visual match).
- `reward/vcer`: Version Conflict Error Rate penalty (penalizing deprecated ManimGL syntax).
- `reward/cover`: Mathematical, visual, numeric, and structural concept coverage.
- `reward/narration`: `VoiceoverScene` structure, bookmark presence, and sync methods.
- `loss/grpo`: GRPO policy optimization loss.

---

## 7. Using the Trained GRPO Model for Inference

Once uploaded to Hugging Face, the GRPO LoRA adapter can be loaded directly with `peft` and `transformers`:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

base_model_id = "Qwen/Qwen3-8B"
grpo_adapter_id = "nabin2004/AOS-qwen3-8b-grpo"

tokenizer = AutoTokenizer.from_pretrained(base_model_id, trust_remote_code=True)
base_model = AutoModelForCausalLM.from_pretrained(
    base_model_id,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True,
)

model = PeftModel.from_pretrained(base_model, grpo_adapter_id)
model.eval()

prompt = [
    {"role": "user", "content": "Write valid Manim Community Edition (CE) Python code.\nUse `from manim import *`. Output a complete Scene class in a ```python fence.\n\nAnimate a 3D Möbius strip rotating with normal vectors pointing outward."}
]

inputs = tokenizer.apply_chat_template(prompt, add_generation_prompt=True, return_tensors="pt").to(model.device)
with torch.no_grad():
    outputs = model.generate(inputs, max_new_tokens=1024, temperature=0.7, top_p=0.9)

print(tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True))
```
