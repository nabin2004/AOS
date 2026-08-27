# Kaggle phase-1 SFT (Qwen2.5-Coder-7B)

Train **only SFT-1** of the Qwen curriculum on [`nabin2004/manim-sft-10k`](https://huggingface.co/datasets/nabin2004/manim-sft-10k): 4-bit LoRA, W&B metrics, Hugging Face adapter push. Default is the **curated 10k** mix (API grounding, error-correction, LaTeX, long/coverage scenes) built from [`nabin2004/manim-sft`](https://huggingface.co/datasets/nabin2004/manim-sft) — the 38k repo is not overwritten. P100 sessions are shorter than one epoch, so training **resumes** from HuggingFace Trainer `checkpoint-*` (local or Hub `last-trainer-checkpoint/`).

Later stages (educlaw, traces, DPO, GRPO, merge, GGUF) stay on [`train_stages.sh`](train_stages.sh) off Kaggle. Merging 7B is a poor fit for 16 GB P100.

## Hardware

| Setting | Value |
|---------|--------|
| Accelerator | **GPU P100** (16 GB) |
| Internet | On |
| Session | ~9 hours (resume across sessions) |

P100 has **no bf16** and **no Flash Attention**, so packing is **off** (avoids TRL cross-sample contamination). Phase 1 is **QLoRA** on chat SFT [`nabin2004/manim-sft-10k`](https://huggingface.co/datasets/nabin2004/manim-sft-10k) (`messages` with system/user/assistant), **not** agent trajectories. The `--kaggle` preset uses fp16 compute, **LoRA r=16 / alpha=32**, full 10k mix, `paged_adamw_8bit`, `seq_len=2048`, checkpoints every **200** steps. Trajectories are SFT-3 on [`train_stages.sh`](train_stages.sh). Subsample with `MAX_SAMPLES=5000` if you only want a short run. Rebuild the mix with [`curate_sft_10k.py`](curate_sft_10k.py).

## Secrets

Add notebook secrets (Add-ons → Secrets):

| Name | Purpose |
|------|---------|
| `HF_TOKEN` | Hugging Face **write** token (dataset + `Qwen/Qwen2.5-Coder-7B-Instruct` + adapter + trainer-checkpoint push) |
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
else
  git -C AOS pull --ff-only
fi
cd AOS
# optional: SAVE_STEPS=100  RESUME_FROM=/kaggle/input/<previous-output>
bash apps/qwenCoder/kaggle_sft_phase1.sh
```

The script **does not create `apps/qwenCoder/.venv` on Kaggle**. It pins **torch 2.7.1+cu118** on system Python (`/usr/bin/python3`), installs SFT deps, then `pip install -e apps/qwenCoder --no-deps`, and runs `python3 run.py` (not `uv run`):

```bash
python3 run.py \
  --kaggle \
  --dataset-repo nabin2004/manim-sft-10k \
  --stage manim \
  --max-samples 0 \
  --save-steps 200 \
  --no-packing \
  --output-dir /kaggle/working/qwen2.5-coder-7b-manim-ft \
  --epochs 1 \
  --report-to wandb \
  --push-to-hub \
  --hub-model-id nabin2004/AOS-qwen2.5-coder-7b-manim-sft
```

Resume is **auto**: if `checkpoint-*` exists under the adapter dir, training continues. If the working directory was wiped, the script downloads `last-trainer-checkpoint/` from the Hub repo. Attach a previous notebook output as a dataset and set `RESUME_FROM=/kaggle/input/<name>/qwen2.5-coder-7b-manim-ft` (or the folder that contains `checkpoint-*`). `--init-adapter` is not used for mid-epoch resume (that path is SFT-2/SFT-3 only).

## Outputs

| Artifact | Location |
|----------|----------|
| LoRA adapter | `/kaggle/working/qwen2.5-coder-7b-manim-ft` |
| Trainer checkpoints | `.../checkpoint-*` (keeps the last 2 locally) |
| Hub adapter | [`nabin2004/AOS-qwen2.5-coder-7b-manim-sft`](https://huggingface.co/nabin2004/AOS-qwen2.5-coder-7b-manim-sft) |
| Hub trainer state | same repo, `last-trainer-checkpoint/` |
| W&B | project `aos-qwen-sft`, run `qwen2.5-coder-7b-manim-sft-manim` |

## Env knobs

Prefix the bash cell or export before the script:

```bash
EPOCHS=1
SEQ_LEN=1024          # if CUDA OOM
DATASET_REPO=nabin2004/manim-sft-10k
MAX_SAMPLES=0         # default full curated 10k; 5000 = subsample
SAVE_STEPS=200        # or 100 for denser checkpoints
RESUME=auto           # auto | 1/always | 0/never
RESUME_FROM=          # /kaggle/input/<previous-output>/...
PACKING=0             # 1 only if Flash Attention is available (not P100)
SKIP_PREFLIGHT=1
SKIP_TRAIN=1          # reuse an existing adapter dir (no train/push)
SKIP_TORCH_REINSTALL=1  # T4 only: keep system torch
KEEP_WANDB_ENV=1      # keep leftover WANDB_RUN_NAME from the notebook
HUB_MODEL_ID=nabin2004/AOS-qwen2.5-coder-7b-manim-sft
HUB_CHECKPOINT_ID=    # default = HUB_MODEL_ID
REPORT_TO=wandb       # or none
ADAPTER_DIR=/kaggle/working/qwen2.5-coder-7b-manim-ft
```

`--kaggle` also applies automatically when `KAGGLE_KERNEL_RUN_TYPE` is set.

## Troubleshooting

- **P100 `sm_60` / `ops.cu` / “no kernel image”**: default PyPI torch is CUDA 13 (`2.13+cu130`) and has no Pascal kernels. On Kaggle the script **never runs `uv sync`**, deletes `apps/qwenCoder/.venv` if present, and trains with **system Python** + **torch 2.7.1+cu118**. `pip install -e . --no-deps` so `pyproject.toml` cannot pull torch 2.13 back in. After other deps install, torch is re-pinned.
- **Do not `uv run` on Kaggle** — that creates `.venv` with cu130 and overwrites the fix.
- **T4 (`sm_75`)**: `SKIP_TORCH_REINSTALL=1`.
- **W&B run named `gemma4-…`**: leftover `WANDB_RUN_NAME` in the notebook. The script unsets it unless `KEEP_WANDB_ENV=1`.
- **OOM**: `SEQ_LEN=1024` (keep batch size 1). Do not turn packing on on P100.
- **Session timeout / unfinished epoch**: default is the **curated 10k** (~1250 steps/epoch at batch 1 × accum 8). Re-run the same cell; it resumes from local `checkpoint-*` or Hub `last-trainer-checkpoint/`. Do not mix a 5k-run or 38k-run checkpoint with this mix. `RESUME=0` starts over.
- **No W&B**: missing `WANDB_API_KEY`; script falls back to `REPORT_TO=none`.
- **Hub push fails**: token needs write access to `HUB_MODEL_ID`.
- If the CUDA smoke check passes but training still dies in bitsandbytes `ops.cu`, pin an older `bitsandbytes` in a follow-up.
- **GradScaler / BF16 or `Attempting to unscale FP16 gradients`**: PEFT creates LoRA in Qwen's BF16 dtype. P100 cannot unscale BF16; casting LoRA to FP16 also fails. After the trainer wraps the model, adapters are cast to **FP32**. Keep `fp16=True, bf16=False` and 4-bit compute dtype FP16. Expect `trainable dtypes: ['torch.float32']`.
