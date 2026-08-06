#!/usr/bin/env bash
# RunPod end-to-end SFT: preflight → train+push adapter → merge+push → GGUF+push.
#
# Usage (from repo root on a RunPod A100 80GB pod with /workspace mounted):
#   export HF_TOKEN=hf_...
#   # optional: export WANDB_API_KEY=...
#   bash apps/sft/train.sh
#
# Env knobs:
#   EPOCHS=1              training epochs (default 1)
#   SEQ_LEN=              if set, passed as --seq-len (e.g. 2048 on 40GB GPUs)
#   REPORT_TO=            override logging; default none unless WANDB_API_KEY is set
#   LLAMA_CPP_DIR=        llama.cpp path (default /workspace/llama.cpp)
#   WORKSPACE=            artifact root (default /workspace)
#   SKIP_TRAIN=1          skip SFT (reuse existing adapter dir)
#   SKIP_MERGE=1          skip merge (reuse existing merged dir)
#   SKIP_GGUF=1           skip GGUF export + push

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

WORKSPACE="${WORKSPACE:-/workspace}"
ADAPTER_DIR="${ADAPTER_DIR:-${WORKSPACE}/gemma4-31b-manim-ft}"
MERGED_DIR="${MERGED_DIR:-${WORKSPACE}/gemma4-31b-manim-merged}"
GGUF_DIR="${GGUF_DIR:-${WORKSPACE}/gemma4-31b-manim-gguf}"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-${WORKSPACE}/llama.cpp}"
EPOCHS="${EPOCHS:-1}"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "ERROR: HF_TOKEN is required (gated Gemma download + Hub pushes)." >&2
  exit 1
fi

if [[ -z "${REPORT_TO:-}" ]]; then
  if [[ -n "${WANDB_API_KEY:-}" ]]; then
    REPORT_TO=wandb
  else
    REPORT_TO=none
  fi
fi

echo "==> Repo: ${REPO_ROOT}"
echo "==> Adapter: ${ADAPTER_DIR}"
echo "==> Merged:  ${MERGED_DIR}"
echo "==> GGUF:    ${GGUF_DIR}"
echo "==> Epochs:  ${EPOCHS}  report_to=${REPORT_TO}"

if ! command -v uv >/dev/null 2>&1; then
  echo "==> Installing uv"
  pip install -q uv
fi

echo "==> uv sync --package sft"
uv sync --package sft

if [[ "${SKIP_TRAIN:-0}" != "1" ]]; then
  echo "==> Preflight"
  uv run --package sft python apps/sft/preflight_gemma4.py --runpod

  echo "==> Train + push LoRA adapter"
  TRAIN_ARGS=(
    --runpod
    --epochs "${EPOCHS}"
    --report-to "${REPORT_TO}"
    --output-dir "${ADAPTER_DIR}"
    --push-to-hub
  )
  if [[ -n "${SEQ_LEN:-}" ]]; then
    TRAIN_ARGS+=(--seq-len "${SEQ_LEN}")
  fi
  uv run --package sft python apps/sft/run.py "${TRAIN_ARGS[@]}"
else
  echo "==> SKIP_TRAIN=1 — using existing adapter at ${ADAPTER_DIR}"
fi

if [[ "${SKIP_MERGE:-0}" != "1" ]]; then
  echo "==> Merge LoRA → bf16 + push merged Hub repo"
  uv run --package sft python apps/sft/merge_adapter.py \
    --adapter-dir "${ADAPTER_DIR}" \
    --output-dir "${MERGED_DIR}" \
    --push-to-hub
else
  echo "==> SKIP_MERGE=1 — using existing merged model at ${MERGED_DIR}"
fi

ensure_llama_cpp() {
  local quant_bin="${LLAMA_CPP_DIR}/build/bin/llama-quantize"
  if [[ -x "${quant_bin}" ]]; then
    echo "==> llama.cpp already built at ${LLAMA_CPP_DIR}"
    return 0
  fi
  echo "==> Building llama.cpp at ${LLAMA_CPP_DIR}"
  if [[ ! -d "${LLAMA_CPP_DIR}/.git" ]]; then
    git clone https://github.com/ggml-org/llama.cpp "${LLAMA_CPP_DIR}"
  fi
  cmake -S "${LLAMA_CPP_DIR}" -B "${LLAMA_CPP_DIR}/build"
  cmake --build "${LLAMA_CPP_DIR}/build" -j "$(nproc 2>/dev/null || echo 4)"
}

if [[ "${SKIP_GGUF:-0}" != "1" ]]; then
  ensure_llama_cpp
  export LLAMA_CPP_DIR

  echo "==> Export GGUF + push to Hub"
  uv run --package sft python apps/sft/export_gguf.py \
    --model-dir "${MERGED_DIR}" \
    --output-dir "${GGUF_DIR}" \
    --llama-cpp-dir "${LLAMA_CPP_DIR}" \
    --push-to-hub \
    --skip-ollama-create
else
  echo "==> SKIP_GGUF=1 — skipping GGUF export"
fi

echo "==> Done"
echo "    Adapter: ${ADAPTER_DIR}"
echo "    Merged:  ${MERGED_DIR}"
echo "    GGUF:    ${GGUF_DIR}"
