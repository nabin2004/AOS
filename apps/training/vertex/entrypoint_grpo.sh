#!/usr/bin/env bash
set -euo pipefail

# Vertex AI entrypoint for Phase 2 GRPO training.
# Downloads SFT adapter (and optional dataset) from GCS, then runs apps/grpo/run.py.

SFT_LORA_URI="${AOS_SFT_LORA_URI:-}"
SFT_LORA_PATH="${AOS_SFT_LORA_PATH:-/tmp/sft/gemma4-manim-ft}"
DATASET_URI="${AOS_DATASET_URI:-}"
DATASET_PATH="${AOS_DATASET_PATH:-/tmp/data/ManiBench_Pilot_Dataset.json}"
OUTPUT_DIR="${AIP_MODEL_DIR:-/tmp/output/grpo}"
REPORT_TO="${AOS_REPORT_TO:-}"
EXTRA_ARGS=(--no-render)

while [[ $# -gt 0 ]]; do
  case "$1" in
    --sft-lora-uri)
      SFT_LORA_URI="$2"
      shift 2
      ;;
    --sft-lora)
      SFT_LORA_PATH="$2"
      shift 2
      ;;
    --dataset-uri)
      DATASET_URI="$2"
      shift 2
      ;;
    --dataset-path)
      DATASET_PATH="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --report-to)
      REPORT_TO="$2"
      shift 2
      ;;
    --smoke)
      EXTRA_ARGS+=(--smoke)
      shift
      ;;
    --grpo-only)
      EXTRA_ARGS+=(--grpo-only)
      shift
      ;;
    *)
      EXTRA_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -z "${REPORT_TO}" ]]; then
  if [[ -n "${WANDB_API_KEY:-}" ]]; then
    REPORT_TO="wandb"
  else
    REPORT_TO="none"
  fi
fi

if [[ -n "${SFT_LORA_URI}" ]]; then
  python /opt/aos/apps/training/vertex/gcs_download.py prefix "${SFT_LORA_URI}" "${SFT_LORA_PATH}"
fi

if [[ -n "${DATASET_URI}" ]]; then
  mkdir -p "$(dirname "${DATASET_PATH}")"
  python /opt/aos/apps/training/vertex/gcs_download.py file "${DATASET_URI}" "${DATASET_PATH}"
fi

if [[ ! -d "${SFT_LORA_PATH}" ]] && [[ "${EXTRA_ARGS[*]}" != *"--grpo-only"* ]]; then
  echo "ERROR: SFT adapter not found at ${SFT_LORA_PATH}" >&2
  exit 1
fi

mkdir -p "${OUTPUT_DIR}"

cd /opt/aos/apps/grpo
CMD=(python run.py --output-dir "${OUTPUT_DIR}" --report-to "${REPORT_TO}")
if [[ "${EXTRA_ARGS[*]}" != *"--grpo-only"* ]]; then
  CMD+=(--sft-lora "${SFT_LORA_PATH}")
fi
if [[ -f "${DATASET_PATH}" ]]; then
  CMD+=(--dataset-path "${DATASET_PATH}")
fi
CMD+=("${EXTRA_ARGS[@]}")
exec "${CMD[@]}"
