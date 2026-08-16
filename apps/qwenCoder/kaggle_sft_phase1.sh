#!/usr/bin/env bash
# Kaggle phase-1 SFT: Qwen2.5-Coder-7B LoRA on nabin2004/manim-sft.
# Logs to W&B (if WANDB_API_KEY is set) and pushes the adapter to Hugging Face.
#
# From a Kaggle notebook (after exporting secrets — see KAGGLE.md):
#   bash apps/qwenCoder/kaggle_sft_phase1.sh
#
# Env knobs:
#   EPOCHS=1
#   SEQ_LEN=2048          # 1024 if CUDA OOM on P100
#   MAX_SAMPLES=          # optional subsample (e.g. 8000 if the 9h session is tight)
#   SKIP_PREFLIGHT=1
#   SKIP_TRAIN=1
#   SKIP_TORCH_REINSTALL=1   # T4: keep PyPI torch (cu130 is fine on sm_75)
#   TORCH_INDEX_URL=https://download.pytorch.org/whl/cu118
#   KEEP_WANDB_ENV=1         # keep leftover WANDB_RUN_NAME from the notebook
#   HUB_MODEL_ID=nabin2004/AOS-qwen2.5-coder-7b-manim-sft
#   REPORT_TO=wandb|none
#   ADAPTER_DIR=          # default /kaggle/working/qwen2.5-coder-7b-manim-ft on Kaggle

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${SCRIPT_DIR}"

if [[ "${KEEP_WANDB_ENV:-0}" != "1" ]]; then
  unset WANDB_RUN_NAME WANDB_JOB_TYPE || true
fi

DATASET_REPO="${DATASET_REPO:-nabin2004/manim-sft}"
HUB_MODEL_ID="${HUB_MODEL_ID:-nabin2004/AOS-qwen2.5-coder-7b-manim-sft}"
EPOCHS="${EPOCHS:-1}"

if [[ -n "${KAGGLE_KERNEL_RUN_TYPE:-}" ]] || [[ -d /kaggle/working ]]; then
  export UV_LINK_MODE="${UV_LINK_MODE:-copy}"
  WORKSPACE="${WORKSPACE:-/kaggle/working}"
else
  WORKSPACE="${WORKSPACE:-${SCRIPT_DIR}}"
fi
ADAPTER_DIR="${ADAPTER_DIR:-${WORKSPACE}/qwen2.5-coder-7b-manim-ft}"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "ERROR: HF_TOKEN is required (Hub download + adapter push)." >&2
  echo "In a Kaggle notebook, export it from UserSecretsClient first (see KAGGLE.md)." >&2
  exit 1
fi

if [[ -z "${REPORT_TO:-}" ]]; then
  if [[ -n "${WANDB_API_KEY:-}" ]]; then
    REPORT_TO=wandb
  else
    echo "WARNING: WANDB_API_KEY is not set; W&B logging disabled." >&2
    REPORT_TO=none
  fi
fi

echo "==> Qwen phase-1 SFT (Kaggle)"
echo "    dataset=${DATASET_REPO}"
echo "    adapter=${ADAPTER_DIR}"
echo "    hub=${HUB_MODEL_ID}"
echo "    report_to=${REPORT_TO}"
echo "    epochs=${EPOCHS}"

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    return 0
  fi
  echo "==> Installing uv"
  if command -v curl >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${HOME}/.local/bin:${PATH}"
  else
    python3 -m pip install --user uv
    export PATH="${HOME}/.local/bin:${PATH}"
  fi
  if ! command -v uv >/dev/null 2>&1; then
    echo "ERROR: uv is not on PATH after install." >&2
    exit 1
  fi
}

ensure_uv
uv sync

install_p100_torch() {
  if [[ "${SKIP_TORCH_REINSTALL:-0}" == "1" ]]; then
    echo "==> Skipping torch reinstall (SKIP_TORCH_REINSTALL=1)"
    return 0
  fi

  local primary="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu118}"
  local fallback="https://download.pytorch.org/whl/cu126"

  echo "==> Reinstalling Pascal-capable torch (P100 sm_60; PyPI cu130 has no kernels)"
  echo "    index=${primary}"
  uv pip uninstall -y torch torchvision torchaudio || true

  if ! uv pip install torch torchvision torchaudio --index-url "${primary}"; then
    echo "WARNING: ${primary} failed; retrying ${fallback}" >&2
    uv pip uninstall -y torch torchvision torchaudio || true
    uv pip install torch torchvision torchaudio --index-url "${fallback}"
  fi

  uv pip install wrapt || true

  echo "==> CUDA smoke check"
  uv run python - <<'PY'
import sys
import torch

print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
if not torch.cuda.is_available():
    print("ERROR: CUDA is not available in the training venv.", file=sys.stderr)
    sys.exit(1)

name = torch.cuda.get_device_name(0)
major, minor = torch.cuda.get_device_capability(0)
print("device", name, f"sm_{major}{minor}")
try:
    x = torch.zeros(8, device="cuda")
    y = x.sum()
    torch.cuda.synchronize()
    print("smoke_ok", float(y.item()))
except Exception as exc:
    print(
        "ERROR: CUDA kernels cannot run on this GPU (need cu118/cu126, not PyPI cu130).",
        file=sys.stderr,
    )
    print(exc, file=sys.stderr)
    sys.exit(1)
PY
}

install_p100_torch

if [[ "${SKIP_PREFLIGHT:-0}" != "1" ]]; then
  echo "==> Preflight"
  uv run python preflight_qwen.py
fi

if [[ "${SKIP_TRAIN:-0}" != "1" ]]; then
  echo "==> Train LoRA (stage manim)"
  TRAIN_ARGS=(
    --kaggle
    --dataset-repo "${DATASET_REPO}"
    --stage manim
    --output-dir "${ADAPTER_DIR}"
    --epochs "${EPOCHS}"
    --report-to "${REPORT_TO}"
    --push-to-hub
    --hub-model-id "${HUB_MODEL_ID}"
  )
  if [[ -n "${SEQ_LEN:-}" ]]; then
    TRAIN_ARGS+=(--seq-len "${SEQ_LEN}")
  fi
  if [[ -n "${MAX_SAMPLES:-}" ]]; then
    TRAIN_ARGS+=(--max-samples "${MAX_SAMPLES}")
  fi
  uv run python run.py "${TRAIN_ARGS[@]}"
fi

echo "==> Done (phase 1)"
echo "    adapter: ${ADAPTER_DIR}"
echo "    hub:     https://huggingface.co/${HUB_MODEL_ID}"
if [[ "${REPORT_TO}" == "wandb" ]]; then
  echo "    wandb:   project aos-qwen-sft  run qwen2.5-coder-7b-manim-sft-manim"
fi
echo "    later stages: bash ${REPO_ROOT}/apps/qwenCoder/train_stages.sh (not on P100)"
