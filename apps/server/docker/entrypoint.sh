#!/usr/bin/env bash
# Launch merged AOS Gemma 4 31B Manim SFT on vLLM (GPU). No --enable-lora.
#
# Required:
#   HF_TOKEN  — Hugging Face token (Gemma license / private or gated downloads)
#
# Optional env (defaults set in Dockerfile):
#   MODEL_ID, HOST, PORT, MAX_MODEL_LEN, GPU_MEMORY_UTILIZATION,
#   TENSOR_PARALLEL_SIZE, LIMIT_MM_PER_PROMPT, EXTRA_ARGS
#
# Extra CLI flags: pass as container args or set EXTRA_ARGS (space-separated).

set -euo pipefail

MODEL_ID="${MODEL_ID:-nabin2004/AOS-gemma4-31b-manim-merged}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-16384}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.90}"
TENSOR_PARALLEL_SIZE="${TENSOR_PARALLEL_SIZE:-1}"
HF_HOME="${HF_HOME:-/workspace/hf-cache}"

if [[ -z "${HF_TOKEN:-}" ]]; then
  echo "ERROR: HF_TOKEN is not set." >&2
  echo "  Accept the Gemma license and export a Hugging Face token so vLLM can" >&2
  echo "  download ${MODEL_ID}." >&2
  exit 1
fi

mkdir -p "${HF_HOME}" "${HUGGINGFACE_HUB_CACHE:-${HF_HOME}/hub}" \
  "${TRANSFORMERS_CACHE:-${HF_HOME}/transformers}"

echo "AOS vLLM serve (merged model)"
echo "  model:                   ${MODEL_ID}"
echo "  max_model_len:           ${MAX_MODEL_LEN}"
echo "  gpu_memory_utilization:  ${GPU_MEMORY_UTILIZATION}"
echo "  tensor_parallel_size:    ${TENSOR_PARALLEL_SIZE}"
echo "  HF_HOME:                 ${HF_HOME}"
echo "  listen:                  ${HOST}:${PORT}"
if [[ -n "${LIMIT_MM_PER_PROMPT:-}" ]]; then
  echo "  limit_mm_per_prompt:     ${LIMIT_MM_PER_PROMPT}"
fi
echo

CMD=(
  vllm serve "${MODEL_ID}"
  --host "${HOST}"
  --port "${PORT}"
  --max-model-len "${MAX_MODEL_LEN}"
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}"
  --tensor-parallel-size "${TENSOR_PARALLEL_SIZE}"
  --dtype bfloat16
  --enable-auto-tool-choice
  --tool-call-parser gemma4
  --reasoning-parser gemma4
  --async-scheduling
)

if [[ -n "${LIMIT_MM_PER_PROMPT:-}" ]]; then
  CMD+=(--limit-mm-per-prompt "${LIMIT_MM_PER_PROMPT}")
fi

# EXTRA_ARGS: space-separated string for RunPod templates (e.g. "--enforce-eager")
if [[ -n "${EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  EXTRA=(${EXTRA_ARGS})
  CMD+=("${EXTRA[@]}")
fi

# Container CMD / docker run args appended last
CMD+=("$@")

exec "${CMD[@]}"
