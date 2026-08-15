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
#   HUB_MODEL_ID=nabin2004/AOS-qwen2.5-coder-7b-manim-sft
#   REPORT_TO=wandb|none
#   ADAPTER_DIR=          # default /kaggle/working/qwen2.5-coder-7b-manim-ft on Kaggle

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${SCRIPT_DIR}"

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
