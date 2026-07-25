#!/usr/bin/env bash
# Launch Gemma 4 + manim-sft LoRA on vLLM's CPU backend (dev / smoke-test only).
#
# Requires the CPU venv from install-vllm-cpu.sh. Inference is very slow on CPU;
# use a GPU or cloud instance for real workloads.
#
# Usage:
#   source ~/.venvs/aos-vllm/bin/activate
#   ./apps/server/scripts/serve-cpu.sh
#
# Override memory if you have more RAM (value is GiB for the KV cache):
#   VLLM_CPU_KVCACHE_SPACE=6 ./apps/server/scripts/serve-cpu.sh

set -euo pipefail

VLLM_VENV="${VLLM_VENV:-${HOME}/.venvs/aos-vllm}"
BASE_MODEL="${BASE_MODEL:-google/gemma-4-E2B-it}"
LORA_MODULE="${LORA_MODULE:-manim-sft=nabin2004/AOS-gemma4-manim-sft}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
MAX_LORA_RANK="${MAX_LORA_RANK:-64}"

# Default 2 GiB KV cache — tune down if you OOM on a 8–16 GiB laptop.
export VLLM_CPU_KVCACHE_SPACE="${VLLM_CPU_KVCACHE_SPACE:-2}"
export VLLM_CPU_OMP_THREADS_BIND="${VLLM_CPU_OMP_THREADS_BIND:-auto}"

if [[ -f "${VLLM_VENV}/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "${VLLM_VENV}/bin/activate"
fi

if ! command -v vllm >/dev/null 2>&1; then
  echo "vllm not found. Run: ./apps/server/scripts/install-vllm-cpu.sh" >&2
  exit 1
fi

if ! python - <<'PY'; then
import torchvision  # noqa: F401 — must be +cpu build matching torch
from vllm.platforms import current_platform

name = type(current_platform).__name__
if "Cpu" not in name and "CPU" not in name:
    raise SystemExit(1)
PY
  echo "vLLM CPU environment check failed." >&2
  echo "  GPU wheel?     Run: ./apps/server/scripts/install-vllm-cpu.sh" >&2
  echo "  torchvision::nms error? Run: ./apps/server/scripts/repair-vllm-cpu.sh" >&2
  exit 1
fi

echo "CPU vLLM serve (dev only)"
echo "  model:          ${BASE_MODEL}"
echo "  lora:           ${LORA_MODULE}"
echo "  kv cache (GiB): ${VLLM_CPU_KVCACHE_SPACE}"
echo "  max_model_len:  ${MAX_MODEL_LEN}"
echo "  listen:         ${HOST}:${PORT}"
echo

exec vllm serve "${BASE_MODEL}" \
  --enable-lora \
  --max-lora-rank "${MAX_LORA_RANK}" \
  --lora-modules "${LORA_MODULE}" \
  --max-model-len "${MAX_MODEL_LEN}" \
  --dtype bfloat16 \
  --host "${HOST}" \
  --port "${PORT}" \
  "$@"
