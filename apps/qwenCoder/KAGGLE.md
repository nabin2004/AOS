# Kaggle phase-1 SFT (Qwen2.5-Coder-7B)

Train **only SFT-1** of the Qwen curriculum on [`nabin2004/manim-sft`](https://huggingface.co/datasets/nabin2004/manim-sft): 4-bit LoRA, W&B metrics, Hugging Face adapter push.

Later stages (educlaw, traces, DPO, GRPO, merge, GGUF) stay on [`train_stages.sh`](train_stages.sh) off Kaggle. Merging 7B is a poor fit for 16 GB P100.

## Hardware

| Setting | Value |
|---------|--------|
| Accelerator | **GPU P100** (16 GB) |
| Internet | On |
| Session | ~9 hours |

P100 has **no bf16**. The `--kaggle` preset uses fp16, NF4 4-bit, `paged_adamw_8bit`, `seq_len=2048`, and **step checkpoints** (`save_steps=200`) so a kernel kill still leaves a resumable adapter under `/kaggle/working`.

## Secrets

Add notebook secrets (Add-ons → Secrets):

| Name | Purpose |
|------|---------|
| `HF_TOKEN` | Hugging Face **write** token (dataset + `Qwen/Qwen2.5-Coder-7B-Instruct` + adapter push) |
| `WANDB_API_KEY` | Weights & Biases logging (optional but expected) |

Kaggle bash cannot read secrets. Export them in the **first** Python cell:

```python
import os
from kaggle_secrets import UserSecretsClient

secrets = UserSecretsClient()
os.environ["HF_TOKEN"] = secrets.get_secret("HF_TOKEN")
try:
    os.environ["WANDB_API_KEY"] = secrets.get_secret("WANDB_API_KEY")
except Exception:
    print("WANDB_API_KEY missing; training will run without W&B")
```

## Run

```python
%%bash
set -euo pipefail
export UV_LINK_MODE=copy
cd /kaggle/working
if [[ ! -d AOS ]]; then
  git clone https://github.com/nabin2004/AOS.git AOS
fi
cd AOS
bash apps/qwenCoder/kaggle_sft_phase1.sh
```

The script installs `uv` if needed, syncs [`apps/qwenCoder`](.), **reinstalls torch from cu118 (cu126 fallback) into that venv** so P100 `sm_60` works, runs `preflight_qwen.py`, then:

```bash
uv run python run.py \
  --kaggle \
  --dataset-repo nabin2004/manim-sft \
  --stage manim \
  --output-dir /kaggle/working/qwen2.5-coder-7b-manim-ft \
  --epochs 1 \
  --report-to wandb \
  --push-to-hub \
  --hub-model-id nabin2004/AOS-qwen2.5-coder-7b-manim-sft
```

## Outputs

| Artifact | Location |
|----------|----------|
| LoRA adapter | `/kaggle/working/qwen2.5-coder-7b-manim-ft` |
| Hub repo | [`nabin2004/AOS-qwen2.5-coder-7b-manim-sft`](https://huggingface.co/nabin2004/AOS-qwen2.5-coder-7b-manim-sft) |
| W&B | project `aos-qwen-sft`, run `qwen2.5-coder-7b-manim-sft-manim` |

## Env knobs

Prefix the bash cell or export before the script:

```bash
EPOCHS=1
SEQ_LEN=1024          # if CUDA OOM
MAX_SAMPLES=8000      # if one epoch will not finish in 9h (~38k rows)
SKIP_PREFLIGHT=1
SKIP_TRAIN=1          # reuse an existing adapter dir (no train/push)
SKIP_TORCH_REINSTALL=1  # T4 only: keep PyPI torch
TORCH_INDEX_URL=https://download.pytorch.org/whl/cu118
KEEP_WANDB_ENV=1      # keep leftover WANDB_RUN_NAME from the notebook
HUB_MODEL_ID=nabin2004/AOS-qwen2.5-coder-7b-manim-sft
REPORT_TO=wandb       # or none
ADAPTER_DIR=/kaggle/working/qwen2.5-coder-7b-manim-ft
```

`--kaggle` also applies automatically when `KAGGLE_KERNEL_RUN_TYPE` is set.

## Troubleshooting

- **P100 `sm_60` / `ops.cu` / “no kernel image”**: PyPI `torch` is CUDA 13 (`cu130`) and has no Pascal kernels. The script **reinstalls torch into `apps/qwenCoder/.venv`** from [cu118](https://download.pytorch.org/whl/cu118), then falls back to [cu126](https://download.pytorch.org/whl/cu126). Do **not** `!pip install` torch in the notebook kernel — training uses the uv venv, not that kernel.
- **T4 (`sm_75`)**: skip the reinstall with `SKIP_TORCH_REINSTALL=1`.
- **W&B run named `gemma4-…`**: leftover `WANDB_RUN_NAME` in the notebook. The script unsets it unless `KEEP_WANDB_ENV=1`.
- **OOM**: `SEQ_LEN=1024` (keep batch size 1).
- **Session timeout**: checkpoints every 200 steps; re-run with the same `ADAPTER_DIR` after lowering `MAX_SAMPLES`, or continue later with `--init-adapter` on a larger GPU via `train_stages.sh`.
- **No W&B**: missing `WANDB_API_KEY`; script falls back to `REPORT_TO=none`.
- **Hub push fails**: token needs write access to `HUB_MODEL_ID`.
- If the CUDA smoke check passes but training still dies in bitsandbytes `ops.cu`, pin an older `bitsandbytes` in a follow-up (do not guess a pin until torch is confirmed Pascal-capable).
