# Running ManiBench GRPO on Kaggle (Dual T4 / P100)

This guide details how to run the end-to-end Group Relative Policy Optimization (GRPO) training pipeline for mathematical animation synthesis on Kaggle GPU instances.

---

## 1. Accelerator Recommendation

- **Recommended**: **GPU T4 x 2** (Dual NVIDIA T4, 32 GB total VRAM).
  - *Why*: GRPO samples multiple completions per prompt ($G=4$ to $8$ parallel generations). Dual T4 provides 32 GB total VRAM, native bfloat16/4-bit QLoRA support with `bitsandbytes`, and fast parallel rollouts.
- **Alternative**: **GPU P100** (Single NVIDIA Tesla P100, 16 GB VRAM).
  - *Why*: Supported fallback for single-GPU budget training.

---

## 2. Kaggle Notebook Setup

### Step 1: Create Notebook & Configure Hardware
1. Go to [kaggle.com/code](https://www.kaggle.com/code) → **New Notebook**.
2. Under **Notebook settings** (right sidebar):
   - **Accelerator**: Select **GPU T4 x 2** (or GPU P100).
   - **Internet**: Toggle **ON** (required for downloading Hugging Face models and dataset splits).

### Step 2: Add Secrets
1. In the Kaggle notebook menu, go to **Add-ons** → **Secrets**.
2. Add your tokens:
   - `HF_TOKEN`: Your Hugging Face user access token (with `write` access for pushing the final adapter).
   - `WANDB_API_KEY`: *(Optional)* Your Weights & Biases API key for live loss and reward tracking.

---

## 3. Execution Commands

### Cell 1: Clone Repository
```python
!git clone https://github.com/nabin2004/AOS.git
%cd AOS
!git pull origin master
```

### Cell 2: Quick Smoke Test (1 Step Verification)
```python
!python3 apps/grpo/run_kaggle_grpo.py --smoke --report-to none
```

### Cell 3: Full End-to-End GRPO Training & Hugging Face Upload
```python
!python3 apps/grpo/run_kaggle_grpo.py \
    --base-model Qwen/Qwen3-8B \
    --sft-lora nabin2004/AOS-qwen3-8b-narrated-dpo \
    --dataset-repo nabin2004/Manim-grpo-dataset-200 \
    --hub-repo nabin2004/AOS-qwen3-8b-grpo \
    --push-to-hub
```

---

## 4. Advanced CLI Options

| Flag | Description | Default |
|---|---|---|
| `--base-model` | Base policy model ID | `Qwen/Qwen3-8B` |
| `--sft-lora` | Initial policy adapter (local dir or HF repo ID) | `nabin2004/AOS-qwen3-8b-narrated-dpo` |
| `--dataset-repo` | Hugging Face Hub dataset repo ID | `nabin2004/Manim-grpo-dataset-200` |
| `--hub-repo` | Hugging Face target model repo for GRPO LoRA | `nabin2004/AOS-qwen3-8b-grpo` |
| `--max-steps` | Maximum optimization steps | `None` (full epochs) |
| `--render` | Enable live headless Manim rendering & OpenCLIP visual scoring | `False` (fast lexical heuristic) |
| `--report-to` | Logging backend (`wandb` or `none`) | `wandb` |
| `--push-to-hub` | Automatically upload final adapter to Hugging Face | `False` |

---

## 5. Output Artifacts

- **GRPO LoRA Checkpoint**: Saved locally to `./apps/grpo/grpo_qwen_manim/`
- **Hugging Face Model**: Published to `https://huggingface.co/nabin2004/AOS-qwen3-8b-grpo`
- **W&B Live Telemetry**: Metrics for `reward/exec`, `reward/align`, `reward/vcer`, `reward/cover`, `reward/narration`, `loss/grpo`.
