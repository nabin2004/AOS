#!/usr/bin/env bash
# Collect AOS trajectories with Ollama Qwen, export SFT + preference pairs, optional HF push.
#
# Usage (from repo root):
#   bash apps/qwenCoder/collect_and_export.sh
#   PUSH=1 bash apps/qwenCoder/collect_and_export.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
AGENTS="${REPO_ROOT}/apps/agents"
PROMPTS="${PROMPTS:-${AGENTS}/sft_data_gen/prompts_curriculum_200.jsonl}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5-coder:7b}"

export AOS_MODEL_PROFILE="${AOS_MODEL_PROFILE:-local}"
export AOS_CODER_MODEL="${AOS_CODER_MODEL:-ollama:${OLLAMA_MODEL}}"

echo "==> Ensure Ollama model ${OLLAMA_MODEL}"
if command -v ollama >/dev/null 2>&1; then
  ollama pull "${OLLAMA_MODEL}" || true
else
  echo "WARNING: ollama not on PATH"
fi

cd "${AGENTS}"
echo "==> Collect traces from ${PROMPTS}"
uv run python sft_data_gen/collect_traces.py --prompts "${PROMPTS}" ${COLLECT_EXTRA:-}

echo "==> Export tool_trace SFT (prefer has_audio=true gold)"
uv run python export_local_sft.py --format tool_trace --train-split 0.9 --require-audio

echo "==> Build preference pairs"
uv run python build_preference_pairs.py --train-split 0.9

if [[ "${PUSH:-0}" == "1" ]]; then
  cd "${SCRIPT_DIR}"
  uv run python upload_dataset.py
fi

echo "==> Done. Next: bash apps/qwenCoder/train.sh"
