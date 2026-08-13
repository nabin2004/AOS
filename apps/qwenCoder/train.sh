#!/usr/bin/env bash
# End-to-end Qwen2.5-Coder-7B SFT: preflight → train+push → merge+push → GGUF+push.
#
# Usage (from repo root on a GPU machine):
#   export HF_TOKEN=hf_...
#   bash apps/qwenCoder/train.sh
#
# Env knobs:
#   EPOCHS=1
#   DATA_PATH=.../tool_trace.train.jsonl
#   SKIP_TRAIN=1 | SKIP_MERGE=1 | SKIP_GGUF=1
#   LLAMA_CPP_DIR=/workspace/llama.cpp

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${SCRIPT_DIR}"

WORKSPACE="${WORKSPACE:-${SCRIPT_DIR}}"
ADAPTER_DIR="${ADAPTER_DIR:-${WORKSPACE}/qwen2.5-coder-7b-manim-ft}"
MERGED_DIR="${MERGED_DIR:-${WORKSPACE}/qwen2.5-coder-7b-manim-merged}"
GGUF_DIR="${GGUF_DIR:-${WORKSPACE}/qwen2.5-coder-7b-manim-gguf}"
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-${WORKSPACE}/llama.cpp}"
EPOCHS="${EPOCHS:-1}"
DATA_PATH="${DATA_PATH:-${REPO_ROOT}/apps/agents/export_traces/coder_sft/tool_trace.train.jsonl}"
REPORT_TO="${REPORT_TO:-wandb}"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "ERROR: HF_TOKEN is required for Hub download/push." >&2
  exit 1
fi

echo "==> Qwen SFT e2e"
echo "    adapter=${ADAPTER_DIR}"
echo "    merged=${MERGED_DIR}"
echo "    gguf=${GGUF_DIR}"
echo "    data=${DATA_PATH}"

uv sync

echo "==> Preflight"
uv run python preflight_qwen.py

if [[ "${SKIP_TRAIN:-0}" != "1" ]]; then
  echo "==> Train LoRA"
  TRAIN_ARGS=(--output-dir "${ADAPTER_DIR}" --epochs "${EPOCHS}" --report-to "${REPORT_TO}" --push-to-hub)
  if [[ -f "${DATA_PATH}" ]]; then
    TRAIN_ARGS+=(--data-path "${DATA_PATH}")
  else
    echo "WARNING: ${DATA_PATH} missing; falling back to Hub dataset"
  fi
  uv run python run.py "${TRAIN_ARGS[@]}"
fi

if [[ "${SKIP_MERGE:-0}" != "1" ]]; then
  echo "==> Merge adapter"
  uv run python merge_adapter.py \
    --adapter-dir "${ADAPTER_DIR}" \
    --output-dir "${MERGED_DIR}" \
    --push-to-hub
fi

if [[ "${SKIP_GGUF:-0}" != "1" ]]; then
  if [[ ! -d "${LLAMA_CPP_DIR}" ]]; then
    echo "==> Cloning llama.cpp"
    git clone --depth 1 https://github.com/ggml-org/llama.cpp "${LLAMA_CPP_DIR}"
    cmake -S "${LLAMA_CPP_DIR}" -B "${LLAMA_CPP_DIR}/build"
    cmake --build "${LLAMA_CPP_DIR}/build" -j
  fi
  echo "==> Export GGUF"
  uv run python export_gguf.py \
    --model-dir "${MERGED_DIR}" \
    --output-dir "${GGUF_DIR}" \
    --llama-cpp-dir "${LLAMA_CPP_DIR}" \
    --skip-ollama-create \
    --push-to-hub
fi

echo "==> Done"
echo "    ollama create aos-qwen2.5-coder-7b-manim -f ${GGUF_DIR}/Modelfile"
