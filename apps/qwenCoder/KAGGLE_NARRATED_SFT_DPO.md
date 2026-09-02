# Kaggle One-Click Continued SFT & DPO Pipeline: Manim Voiceover

End-to-end curriculum for fine-tuning and aligning **`Qwen/Qwen3-8B`** (or `Qwen/Qwen2.5-Coder-7B-Instruct`) to generate voiceover-synchronized Manim Community Edition animation code using **Continued SFT** and **Direct Preference Optimization (DPO)**.

---

## Pipeline Architecture

```
                                  [400 Narrated Voiceover Trajectories]
                                                    │
                   ┌────────────────────────────────┴───────────────────────────────┐
                   ▼                                                                ▼
       [Continued SFT Dataset]                                            [DPO Preference Dataset]
(System + User Prompt -> VoiceoverScene)                              (Prompt, Chosen: VoiceoverScene,
                   │                                                   Rejected: Silent Scene)
                   ▼                                                                │
 [Stage 1: Continued QLoRA SFT]                                                     │
   Base: Qwen/Qwen3-8B                                                              │
   Init: nabin2004/AOS-qwen3-8b-adapter                                             │
                   │                                                                │
                   ▼                                                                ▼
 [Push SFT LoRA: nabin2004/AOS-qwen3-8b-narrated-adapter] ───────────► [Stage 2: Direct Preference Optimization]
                                                                        Policy: Base + Narrated SFT LoRA
                                                                        Beta: 0.1 (KL penalty)
                                                                                    │
                                                                                    ▼
                                                                [Push DPO LoRA: nabin2004/AOS-qwen3-8b-narrated-dpo]
```

---

## Datasets on Hugging Face

| Dataset | Hub Repository | Description |
|---|---|---|
| **Narrated Trajectories** | [`nabin2004/AOS-Narrated-Manim-400`](https://huggingface.co/datasets/nabin2004/AOS-Narrated-Manim-400) | 400 executable `VoiceoverScene` scripts with `GTTSService()` |
| **DPO Preference Pairs** | [`nabin2004/manim-narrated-dpo-400`](https://huggingface.co/datasets/nabin2004/manim-narrated-dpo-400) | 400 aligned pairs (`chosen` = VoiceoverScene, `rejected` = silent Scene) |

---

## Target Model Repositories on Hugging Face

| Stage | Target Repository | Base LLM |
|---|---|---|
| **Stage 1 (Continued SFT)** | [`nabin2004/AOS-qwen3-8b-narrated-adapter`](https://huggingface.co/nabin2004/AOS-qwen3-8b-narrated-adapter) | `Qwen/Qwen3-8B` |
| **Stage 2 (DPO Alignment)** | [`nabin2004/AOS-qwen3-8b-narrated-dpo`](https://huggingface.co/nabin2004/AOS-qwen3-8b-narrated-dpo) | `Qwen/Qwen3-8B` |

---

## One-Click Super Simple Kaggle Notebook Code

In a Kaggle Notebook code cell with a **P100 (or T4) GPU** and **Internet ON**:

```python
# Cell 1: Setup Secrets
import os
from kaggle_secrets import UserSecretsClient

secrets = UserSecretsClient()
os.environ["HF_TOKEN"] = secrets.get_secret("HF_TOKEN")

try:
    os.environ["WANDB_API_KEY"] = secrets.get_secret("WANDB_API_KEY")
except Exception:
    pass

# Cell 2: Pull Latest Repo & Run Full Continued SFT + DPO Pipeline
!cd /kaggle/working && git clone https://github.com/nabin2004/AOS.git 2>/dev/null || git -C /kaggle/working/AOS pull
!python3 /kaggle/working/AOS/apps/qwenCoder/run_kaggle_narrated.py
```

---

## Standalone Commands (Local or Cloud)

### 1. Build Aligned Datasets
```bash
cd apps/qwenCoder
uv run python prepare_narrated_datasets.py --push-dpo
```

### 2. Run Continued SFT Only
```bash
uv run python run_narrated_sft.py \
    --base-model Qwen/Qwen3-8B \
    --init-adapter nabin2004/AOS-qwen3-8b-adapter \
    --hub-adapter-repo nabin2004/AOS-qwen3-8b-narrated-adapter \
    --push-to-hub
```

### 3. Run DPO Alignment Only
```bash
uv run python run_narrated_dpo.py \
    --base-model Qwen/Qwen3-8B \
    --sft-adapter nabin2004/AOS-qwen3-8b-narrated-adapter \
    --hub-dpo-repo nabin2004/AOS-qwen3-8b-narrated-dpo \
    --beta 0.1 \
    --push-to-hub
```
