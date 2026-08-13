#!/usr/bin/env bash
# Staged Qwen2.5-Coder-7B curriculum:
#   SFT manim-sft → SFT educlaw (20k) → SFT AOS-Trajectories → DPO → GRPO ManiBench
#
# Usage (GPU machine, from repo root or apps/qwenCoder):
#   cp apps/training/.env.example apps/training/.env   # set WANDB_API_KEY
#   export HF_TOKEN=hf_...
#   bash apps/qwenCoder/train_stages.sh
#
# Skip stages with env flags:
#   SKIP_PREFLIGHT=1 SKIP_SFT_MANIM=1 SKIP_SFT_EDUCLAW=1 SKIP_SFT_TRACES=1
#   SKIP_DPO=1 SKIP_GRPO=1
#   RUN_MERGE=1 RUN_GGUF=1   # packaging off by default
#   SMOKE=1                  # tiny overfit on every stage
#   EDUCLAW_MAX_SAMPLES=20000
#   REPORT_TO=wandb|none
#   PUSH_TO_HUB=1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${SCRIPT_DIR}"

ADAPTER_DIR="${ADAPTER_DIR:-${SCRIPT_DIR}/qwen2.5-coder-7b-manim-ft}"
DPO_DIR="${DPO_DIR:-${REPO_ROOT}/apps/dpo/qwen2.5-coder-7b-manim-dpo}"
GRPO_DIR="${GRPO_DIR:-${REPO_ROOT}/apps/grpo/grpo_qwen_manim}"
MERGED_DIR="${MERGED_DIR:-${SCRIPT_DIR}/qwen2.5-coder-7b-manim-merged}"
GGUF_DIR="${GGUF_DIR:-${SCRIPT_DIR}/qwen2.5-coder-7b-manim-gguf}"
PREF_TRAIN="${PREF_TRAIN:-${REPO_ROOT}/apps/agents/export_traces/coder_sft/preference/train.jsonl}"
PREF_VAL="${PREF_VAL:-${REPO_ROOT}/apps/agents/export_traces/coder_sft/preference/val.jsonl}"
EPOCHS="${EPOCHS:-1}"
EDUCLAW_MAX_SAMPLES="${EDUCLAW_MAX_SAMPLES:-20000}"
REPORT_TO="${REPORT_TO:-wandb}"
SMOKE="${SMOKE:-0}"
PUSH_TO_HUB="${PUSH_TO_HUB:-0}"

COMMON_ARGS=(--output-dir "${ADAPTER_DIR}" --epochs "${EPOCHS}" --report-to "${REPORT_TO}")
if [[ "${SMOKE}" == "1" ]]; then
  COMMON_ARGS+=(--smoke)
fi
if [[ "${PUSH_TO_HUB}" == "1" ]]; then
  COMMON_ARGS+=(--push-to-hub)
fi

echo "==> Qwen staged curriculum"
echo "    adapter=${ADAPTER_DIR}"
echo "    dpo=${DPO_DIR}"
echo "    grpo=${GRPO_DIR}"
echo "    report_to=${REPORT_TO} smoke=${SMOKE}"

uv sync

if [[ "${SKIP_PREFLIGHT:-0}" != "1" ]]; then
  echo "==> Preflight"
  uv run python preflight_qwen.py
fi

# --- SFT-1: general Manim codegen ---
if [[ "${SKIP_SFT_MANIM:-0}" != "1" ]]; then
  echo "==> SFT-1 manim-sft"
  uv run python run.py \
    --dataset-repo nabin2004/manim-sft \
    --stage manim \
    "${COMMON_ARGS[@]}"
fi

# --- SFT-2: light curriculum / API ---
if [[ "${SKIP_SFT_EDUCLAW:-0}" != "1" ]]; then
  echo "==> SFT-2 educlaw-manim-sft (max ${EDUCLAW_MAX_SAMPLES})"
  uv run python run.py \
    --dataset-repo nabin2004/educlaw-manim-sft \
    --dataset-split train \
    --max-samples "${EDUCLAW_MAX_SAMPLES}" \
    --init-adapter "${ADAPTER_DIR}" \
    --stage educlaw \
    "${COMMON_ARGS[@]}"
fi

# --- SFT-3: agent tool traces ---
if [[ "${SKIP_SFT_TRACES:-0}" != "1" ]]; then
  echo "==> SFT-3 AOS-Trajectories tool_trace"
  TRACE_ARGS=(
    --dataset-repo nabin2004/AOS-Trajectories
    --dataset-file tool_trace/train.jsonl
    --init-adapter "${ADAPTER_DIR}"
    --stage traces
    "${COMMON_ARGS[@]}"
  )
  LOCAL_TRACE="${REPO_ROOT}/apps/agents/export_traces/coder_sft/tool_trace.train.jsonl"
  if [[ -f "${LOCAL_TRACE}" ]]; then
    echo "    using local ${LOCAL_TRACE}"
    TRACE_ARGS=(
      --data-path "${LOCAL_TRACE}"
      --init-adapter "${ADAPTER_DIR}"
      --stage traces
      "${COMMON_ARGS[@]}"
    )
  fi
  uv run python run.py "${TRACE_ARGS[@]}"
fi

# --- DPO ---
if [[ "${SKIP_DPO:-0}" != "1" ]]; then
  echo "==> DPO preference"
  if [[ ! -f "${PREF_TRAIN}" ]]; then
    echo "ERROR: preference file missing: ${PREF_TRAIN}" >&2
    echo "Run: cd apps/agents && uv run python build_preference_pairs.py" >&2
    exit 1
  fi
  cd "${REPO_ROOT}/apps/dpo"
  uv sync
  DPO_ARGS=(
    --sft-lora "${ADAPTER_DIR}"
    --data-path "${PREF_TRAIN}"
    --output-dir "${DPO_DIR}"
    --report-to "${REPORT_TO}"
  )
  if [[ -f "${PREF_VAL}" ]]; then
    DPO_ARGS+=(--eval-path "${PREF_VAL}")
  fi
  if [[ "${SMOKE}" == "1" ]]; then
    DPO_ARGS+=(--smoke)
  fi
  if [[ "${PUSH_TO_HUB}" == "1" ]]; then
    DPO_ARGS+=(--push-to-hub)
  fi
  uv run python run.py "${DPO_ARGS[@]}"
  cd "${SCRIPT_DIR}"
fi

# --- GRPO on ManiBench (stacked on DPO if present, else SFT) ---
if [[ "${SKIP_GRPO:-0}" != "1" ]]; then
  echo "==> GRPO ManiBench"
  GRPO_BASE="${DPO_DIR}"
  if [[ ! -d "${GRPO_BASE}" ]]; then
    GRPO_BASE="${ADAPTER_DIR}"
  fi
  cd "${REPO_ROOT}/apps/grpo"
  uv sync
  GRPO_ARGS=(
    --base qwen
    --sft-lora "${GRPO_BASE}"
    --output-dir "${GRPO_DIR}"
    --report-to "${REPORT_TO}"
  )
  if [[ "${SMOKE}" == "1" ]]; then
    GRPO_ARGS+=(--smoke)
  fi
  if [[ -n "${PROMPTS_PATH:-}" ]]; then
    GRPO_ARGS+=(--prompts-path "${PROMPTS_PATH}")
  fi
  uv run python run.py "${GRPO_ARGS[@]}"
  cd "${SCRIPT_DIR}"
fi

# --- Optional packaging ---
if [[ "${RUN_MERGE:-0}" == "1" ]]; then
  echo "==> Merge adapter"
  MERGE_SRC="${ADAPTER_DIR}"
  if [[ -d "${DPO_DIR}" ]]; then
    MERGE_SRC="${DPO_DIR}"
  fi
  MERGE_ARGS=(--adapter-dir "${MERGE_SRC}" --output-dir "${MERGED_DIR}")
  if [[ "${PUSH_TO_HUB}" == "1" ]]; then
    MERGE_ARGS+=(--push-to-hub)
  fi
  uv run python merge_adapter.py "${MERGE_ARGS[@]}"
fi

if [[ "${RUN_GGUF:-0}" == "1" ]]; then
  echo "==> Export GGUF"
  GGUF_ARGS=(
    --model-dir "${MERGED_DIR}"
    --output-dir "${GGUF_DIR}"
    --skip-ollama-create
  )
  if [[ "${PUSH_TO_HUB}" == "1" ]]; then
    GGUF_ARGS+=(--push-to-hub)
  fi
  uv run python export_gguf.py "${GGUF_ARGS[@]}"
fi

echo "==> Staged training complete"
echo "    SFT:  ${ADAPTER_DIR}"
echo "    DPO:  ${DPO_DIR}"
echo "    GRPO: ${GRPO_DIR}"
