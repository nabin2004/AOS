#!/usr/bin/env bash
# Kaggle End-to-End Qwen3-8B Pipeline Script (P100 GPU)
# Runs QLoRA SFT on nabin2004/manim-aos-5k400, merges adapter, multi-quantizes GGUF (Q4_K_M + Q8_0),
# and pushes artifacts to Hugging Face.
#
# On Kaggle this script uses *system* Python (torch 2.7.1+cu118 for P100 sm_60).
# It does NOT create apps/qwenCoder/.venv and does NOT run `uv sync` / `uv run`.
#
# Usage from Kaggle Notebook:
#   bash apps/qwenCoder/kaggle_qwen3_8b_e2e.sh

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

MODEL_ID="${MODEL_ID:-Qwen/Qwen3-8B}"
DATASET_REPO="${DATASET_REPO:-nabin2004/manim-aos-5k400}"
HUB_ADAPTER_REPO="${HUB_ADAPTER_REPO:-nabin2004/AOS-qwen3-8b-adapter}"
HUB_MERGED_REPO="${HUB_MERGED_REPO:-nabin2004/AOS-Qwen3-8B-Merged}"
HUB_GGUF_REPO="${HUB_GGUF_REPO:-nabin2004/AOS-Qwen3-8B-GGUF}"
EPOCHS="${EPOCHS:-1}"
SEQ_LEN="${SEQ_LEN:-2048}"
SAVE_STEPS="${SAVE_STEPS:-200}"

if [[ "${ON_KAGGLE}" == "1" ]]; then
  WORKSPACE="${WORKSPACE:-/kaggle/working}"
else
  WORKSPACE="${WORKSPACE:-${SCRIPT_DIR}}"
fi

ADAPTER_DIR="${ADAPTER_DIR:-${WORKSPACE}/qwen3-8b-manim-ft}"
MERGED_DIR="${MERGED_DIR:-${WORKSPACE}/qwen3-8b-manim-merged}"
GGUF_DIR="${GGUF_DIR:-${WORKSPACE}/qwen3-8b-manim-gguf}"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "ERROR: HF_TOKEN is required for Hugging Face uploads." >&2
  echo "In a Kaggle notebook, export it from UserSecretsClient first." >&2
  exit 1
fi

echo "================================================================="
echo "🚀 Kaggle Qwen3-8B End-to-End Pipeline Initialization"
echo "   Model ID:     ${MODEL_ID}"
echo "   Dataset:      ${DATASET_REPO}"
echo "   On Kaggle:    ${ON_KAGGLE}"
echo "   Adapter Repo: ${HUB_ADAPTER_REPO}"
echo "   Merged Repo:  ${HUB_MERGED_REPO}"
echo "   GGUF Repo:    ${HUB_GGUF_REPO}"
echo "================================================================="

install_p100_torch_system() {
  if [[ "${SKIP_TORCH_REINSTALL:-0}" == "1" ]]; then
    echo "==> Skipping torch reinstall (SKIP_TORCH_REINSTALL=1)"
    return 0
  fi

  local index="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu118}"
  echo "==> Pinning system torch 2.7.1+cu118 for P100 sm_60"
  "${PYTHON}" -m pip uninstall -y torch torchvision torchaudio || true
  "${PYTHON}" -m pip install \
    torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 \
    --index-url "${index}"
}

install_kaggle_deps() {
  echo "==> Installing SFT & quantization deps into system Python"
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

  if [[ "${SKIP_TORCH_REINSTALL:-0}" != "1" ]]; then
    echo "==> Re-pinning torch 2.7.1+cu118 after dep install"
    "${PYTHON}" -m pip install \
      torch==2.7.1 torchvision==0.22.1 torchaudio==2.7.1 \
      --index-url "${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu118}"
  fi

  echo "==> Editable install of qwen-coder-sft --no-deps"
  "${PYTHON}" -m pip install -e "${SCRIPT_DIR}" --no-deps
}

cuda_smoke() {
  echo "==> CUDA smoke check (${PYTHON})"
  "${PYTHON}" - <<'PY'
import sys
import torch

print("Torch:", torch.__version__)
print("CUDA:", torch.version.cuda)
print("Available:", torch.cuda.is_available())
if not torch.cuda.is_available():
    print("ERROR: CUDA is not available.", file=sys.stderr)
    sys.exit(1)

print("GPU:", torch.cuda.get_device_name(0))
print("Capability:", torch.cuda.get_device_capability(0))
x = torch.randn(256, 256, device="cuda")
y = x @ x
torch.cuda.synchronize()
print("CUDA SMOKE TEST PASSED")
PY
}

if [[ "${ON_KAGGLE}" == "1" ]]; then
  echo "==> Kaggle environment detected: setting up system Python"
  rm -rf "${SCRIPT_DIR}/.venv"
  install_p100_torch_system
  install_kaggle_deps
  cuda_smoke
  RUN_PY=("${PYTHON}")
else
  echo "==> Local environment detected: running via uv"
  RUN_PY=(uv run python)
fi

echo "==> Launching Master Pipeline: run_e2e_qwen3.py"
"${RUN_PY[@]}" run_e2e_qwen3.py \
  --model-id "${MODEL_ID}" \
  --dataset-repo "${DATASET_REPO}" \
  --adapter-dir "${ADAPTER_DIR}" \
  --merged-dir "${MERGED_DIR}" \
  --gguf-dir "${GGUF_DIR}" \
  --hub-adapter-repo "${HUB_ADAPTER_REPO}" \
  --hub-merged-repo "${HUB_MERGED_REPO}" \
  --hub-gguf-repo "${HUB_GGUF_REPO}" \
  --quantize-types Q4_K_M Q8_0 \
  --epochs "${EPOCHS}" \
  --seq-len "${SEQ_LEN}" \
  --save-steps "${SAVE_STEPS}" \
  --kaggle \
  --push-to-hub

echo "==> Qwen3-8B End-to-End Pipeline Finished Successfully!"
