#!/usr/bin/env bash
# Kaggle phase-1 SFT: Qwen2.5-Coder-7B LoRA on nabin2004/manim-sft.
# Logs to W&B (if WANDB_API_KEY is set) and pushes the adapter to Hugging Face.
#
# On Kaggle this script uses *system* Python (torch 2.7.1+cu118 for P100 sm_60).
# It does NOT create apps/qwenCoder/.venv and does NOT run `uv sync` / `uv run`.
# Local machines keep the uv project venv.
#
# From a Kaggle notebook (after exporting secrets — see KAGGLE.md):
#   bash apps/qwenCoder/kaggle_sft_phase1.sh
#
# Env knobs:
#   EPOCHS=1
#   SEQ_LEN=2048          # 1024 if CUDA OOM on P100
#   MAX_SAMPLES=5000      # 0 or all = full ~38k (too slow on P100)
#   PACKING=1             # 0 to disable sequence packing
#   SKIP_PREFLIGHT=1
#   SKIP_TRAIN=1
#   SKIP_TORCH_REINSTALL=1   # T4: keep whatever torch is already on system Python
#   KEEP_WANDB_ENV=1         # keep leftover WANDB_RUN_NAME from the notebook
#   HUB_MODEL_ID=nabin2004/AOS-qwen2.5-coder-7b-manim-sft
#   REPORT_TO=wandb|none
#   ADAPTER_DIR=          # default /kaggle/working/qwen2.5-coder-7b-manim-ft on Kaggle

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${SCRIPT_DIR}"

PYTHON="${PYTHON:-python3}"
ON_KAGGLE=0
if [[ -n "${KAGGLE_KERNEL_RUN_TYPE:-}" ]] || [[ -d /kaggle/working ]]; then
  ON_KAGGLE=1
fi

if [[ "${KEEP_WANDB_ENV:-0}" != "1" ]]; then
  unset WANDB_RUN_NAME WANDB_JOB_TYPE || true
fi

DATASET_REPO="${DATASET_REPO:-nabin2004/manim-sft}"
HUB_MODEL_ID="${HUB_MODEL_ID:-nabin2004/AOS-qwen2.5-coder-7b-manim-sft}"
EPOCHS="${EPOCHS:-1}"
MAX_SAMPLES="${MAX_SAMPLES:-5000}"

if [[ "${ON_KAGGLE}" == "1" ]]; then
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

echo "==> Qwen phase-1 SFT"
echo "    python=$(command -v "${PYTHON}")"
echo "    kaggle=${ON_KAGGLE}"
echo "    dataset=${DATASET_REPO}"
echo "    max_samples=${MAX_SAMPLES}"
echo "    packing=${PACKING:-1}"
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

install_p100_torch_system() {
  if [[ "${SKIP_TORCH_REINSTALL:-0}" == "1" ]]; then
    echo "==> Skipping torch reinstall (SKIP_TORCH_REINSTALL=1)"
    return 0
  fi

  local index="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu118}"
  echo "==> Pinning system torch 2.7.1+cu118 for P100 sm_60"
  echo "    python=$(command -v "${PYTHON}")"
  echo "    index=${index}"
  "${PYTHON}" -m pip uninstall -y torch torchvision torchaudio || true
  "${PYTHON}" -m pip install \
    torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 \
    --index-url "${index}"
}

install_kaggle_deps() {
  echo "==> Installing SFT deps into system Python (no torch upgrade)"
  "${PYTHON}" -m pip install --upgrade pip
  "${PYTHON}" -m pip install wrapt
  "${PYTHON}" -m pip install \
    "accelerate>=1.0.0" \
    "bitsandbytes>=0.45.0" \
    "datasets>=5.0.0" \
    "huggingface-hub>=0.27.0" \
    "peft>=0.19.1" \
    "transformers>=4.51.0" \
    "trl>=0.19.0" \
    "wandb>=0.19.0"

  # Other packages may pull a newer PyPI torch; pin cu118 again.
  if [[ "${SKIP_TORCH_REINSTALL:-0}" != "1" ]]; then
    echo "==> Re-pinning torch 2.7.1+cu118 after dep install"
    "${PYTHON}" -m pip install \
      torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 \
      --index-url "${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu118}"
  fi

  echo "==> Editable install of qwen-coder-sft --no-deps (must not pull torch 2.13)"
  "${PYTHON}" -m pip install -e "${SCRIPT_DIR}" --no-deps
}

cuda_smoke() {
  echo "==> CUDA smoke check (${PYTHON})"
  "${PYTHON}" - <<'PY'
import sys
import torch

print("Torch:", torch.__version__)
print("CUDA:", torch.version.cuda)
print("available:", torch.cuda.is_available())
print("file:", torch.__file__)
if not torch.cuda.is_available():
    print("ERROR: CUDA is not available.", file=sys.stderr)
    sys.exit(1)

print("GPU:", torch.cuda.get_device_name(0))
print("Capability:", torch.cuda.get_device_capability(0))

if "+cu130" in torch.__version__ or (torch.version.cuda or "").startswith("13"):
    print(
        "ERROR: CUDA 13 torch has no P100 sm_60 kernels. "
        "This process must use torch 2.7.1+cu118 on system Python, not .venv.",
        file=sys.stderr,
    )
    sys.exit(1)

x = torch.randn(256, 256, device="cuda")
y = x @ x
torch.cuda.synchronize()
print("CUDA SMOKE TEST PASSED")
PY
}

if [[ "${ON_KAGGLE}" == "1" ]]; then
  echo "==> Kaggle: using system Python (no uv .venv)"
  rm -rf "${SCRIPT_DIR}/.venv"
  install_p100_torch_system
  install_kaggle_deps
  cuda_smoke
  RUN_PY=("${PYTHON}")
else
  echo "==> Local: using uv project environment"
  ensure_uv
  export UV_LINK_MODE="${UV_LINK_MODE:-copy}"
  uv sync
  RUN_PY=(uv run python)
fi

if [[ "${SKIP_PREFLIGHT:-0}" != "1" ]]; then
  echo "==> Preflight"
  "${RUN_PY[@]}" preflight_qwen.py
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
  if [[ "${MAX_SAMPLES}" == "all" || "${MAX_SAMPLES}" == "0" ]]; then
    TRAIN_ARGS+=(--max-samples 0)
  else
    TRAIN_ARGS+=(--max-samples "${MAX_SAMPLES}")
  fi
  if [[ "${PACKING:-1}" == "0" ]]; then
    TRAIN_ARGS+=(--no-packing)
  else
    TRAIN_ARGS+=(--packing)
  fi
  "${RUN_PY[@]}" run.py "${TRAIN_ARGS[@]}"
fi

echo "==> Done (phase 1)"
echo "    adapter: ${ADAPTER_DIR}"
echo "    hub:     https://huggingface.co/${HUB_MODEL_ID}"
if [[ "${REPORT_TO}" == "wandb" ]]; then
  echo "    wandb:   project aos-qwen-sft  run qwen2.5-coder-7b-manim-sft-manim"
fi
echo "    later stages: bash ${REPO_ROOT}/apps/qwenCoder/train_stages.sh (not on P100)"
